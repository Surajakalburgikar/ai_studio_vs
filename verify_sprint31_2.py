import unittest
from unittest.mock import MagicMock, patch
import os
import json
import time
import shutil
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test DB file
TEST_DB_FILE = "./verify_sprint31_2_temp.db"
if os.path.exists(TEST_DB_FILE):
    try:
        os.remove(TEST_DB_FILE)
    except Exception:
        pass

# Configure environment before imports
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_FILE}"
os.environ["STORY_GENERATOR_PROVIDER"] = "gemini"
os.environ["GEMINI_API_KEY"] = "mock_key_for_testing"

from app.database.base import Base
import app.models  # Register metadata
from app.models.project import Project, VideoType, AspectRatio, ArtStyle, NarrationStyle, VoiceGender
from app.services.ai.providers.gemini_provider import GeminiProvider
from app.services.ai.providers.gemini_model_router import GeminiModelRouter
from app.main import app
from app.database.session import engine as db_engine

# Initialize database schema
Base.metadata.create_all(bind=db_engine)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


class MockUsageMetadata:
    def __init__(self):
        self.prompt_token_count = 100
        self.candidates_token_count = 50
        self.total_token_count = 150


class MockResponse:
    def __init__(self, text):
        self.text = text
        self.usage_metadata = MockUsageMetadata()


class TestSprint31_2GeminiRuntime(unittest.TestCase):

    def setUp(self):
        self.db = TestSessionLocal()
        
        # Reset the shared cooldown state before each test
        from app.services.ai.providers.gemini_model_router import _cooldowns
        _cooldowns.clear()
        
        # Paths for test state & stats
        self.test_dir = "app/runtime_test"
        self.state_file = os.path.join(self.test_dir, "gemini_router_state.json")
        self.stats_file = os.path.join(self.test_dir, "gemini_router_stats.json")
        
        # Clean test directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Patch paths inside GeminiModelRouter module
        self.router_patcher = patch(
            "app.services.ai.providers.gemini_model_router.STATE_FILE", self.state_file
        )
        self.stats_patcher = patch(
            "app.services.ai.providers.gemini_model_router.STATS_FILE", self.stats_file
        )
        self.router_patcher.start()
        self.stats_patcher.start()
        
        self.client = TestClient(app)

    def tearDown(self):
        self.router_patcher.stop()
        self.stats_patcher.stop()
        self.db.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_router_state_persistence_and_restart(self):
        router = GeminiModelRouter(state_file=self.state_file, stats_file=self.stats_file)
        
        # Put gemini-2.5-flash on cooldown
        router.mark_unavailable("gemini-2.5-flash", cooldown_minutes=30)
        router.record_failure("gemini-2.5-flash", "quota_exhausted")
        
        # Check files exist
        self.assertTrue(os.path.exists(self.state_file))
        
        # Simulate restart by instantiating a new router
        new_router = GeminiModelRouter(state_file=self.state_file, stats_file=self.stats_file)
        
        self.assertFalse(new_router.is_model_available("gemini-2.5-flash"))
        self.assertEqual(new_router.last_failure.get("gemini-2.5-flash"), "quota_exhausted")

    def test_statistics_updates_and_summary(self):
        router = GeminiModelRouter(state_file=self.state_file, stats_file=self.stats_file)
        
        router.record_request("gemini-3.5-flash")
        router.record_success("gemini-3.5-flash", 100.0)
        router.record_request("gemini-3.5-flash")
        router.record_success("gemini-3.5-flash", 200.0)
        router.record_request("gemini-3.5-flash")
        router.record_failure("gemini-3.5-flash", "429 Rate Limit")
        
        self.assertTrue(os.path.exists(self.stats_file))
        
        # Verify stats metrics
        stats_data = router.stats["gemini-3.5-flash"]
        self.assertEqual(stats_data["requests"], 3)
        self.assertEqual(stats_data["successful requests"], 2)
        self.assertEqual(stats_data["failed requests"], 1)
        self.assertEqual(stats_data["429 count"], 1)
        self.assertEqual(stats_data["average latency"], 150.0)
        
        # Verify restart reload
        new_router = GeminiModelRouter(state_file=self.state_file, stats_file=self.stats_file)
        self.assertEqual(new_router.stats["gemini-3.5-flash"]["requests"], 3)
        
        # Verify get_stats_summary structure
        summary = new_router.get_stats_summary()
        self.assertIn("overall", summary["average_latency"])
        self.assertEqual(summary["average_latency"]["overall"], 150.0)
        self.assertEqual(summary["failures"]["overall"], 1)

    @patch("google.genai.Client")
    def test_project_model_pinning_and_fallback(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value = MockResponse('{"title": "Epic Story", "episodes": []}')
        
        # Create a new project
        project = Project(
            title="Runtime Test Project",
            description="A test project for model pinning",
            video_type=VideoType.MEDIUM,
            target_duration_seconds=120,
            aspect_ratio=AspectRatio.SIXTEEN_TO_NINE,
            language="English",
            art_style=ArtStyle.ANIME,
            narration_style=NarrationStyle.THIRD_PERSON,
            subtitle_language="English",
            voice_gender=VoiceGender.MALE
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        
        # Verify preferred model is initially None
        self.assertIsNone(project.preferred_story_model)
        
        # Simulate StoryPipeline.execute by defining a frame-like context
        # We patch find_project_id_in_stack to return the project ID
        with patch("app.services.ai.providers.gemini_provider.find_project_id_in_stack", return_value=project.id):
            provider = GeminiProvider()
            provider.router = GeminiModelRouter(state_file=self.state_file, stats_file=self.stats_file)
            
            # Execute generation
            result = provider.generate("Test prompt")
            self.assertIsNotNone(result)
            
            # Check project preferred_story_model was updated (pinned) automatically
            self.db.refresh(project)
            self.assertEqual(project.preferred_story_model, "gemini-2.5-flash")
            
            # Set gemini-2.5-flash on cooldown
            provider.router.mark_unavailable("gemini-2.5-flash", cooldown_minutes=30)
            
            # Run another generation - should fall back to next model (gemini-3.5-flash)
            mock_client.models.generate_content.reset_mock()
            provider.generate("Test prompt 2")
            
            # Assert call was made to gemini-3.5-flash
            mock_client.models.generate_content.assert_called_once()
            args, kwargs = mock_client.models.generate_content.call_args
            self.assertEqual(kwargs["model"], "gemini-3.5-flash")

    def test_api_endpoints(self):
        # Create router instance to initialize stats/state
        router = GeminiModelRouter(state_file=self.state_file, stats_file=self.stats_file)
        router.record_request("gemini-2.5-flash")
        router.record_success("gemini-2.5-flash", 100.0)
        
        # Patch Router instance inside system controller
        with patch("app.api.system.GeminiModelRouter") as mock_router_class:
            mock_router_class.return_value = router
            
            # 1. GET /system/gemini/router
            response = self.client.get("/system/gemini/router")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["current_active_model"], "gemini-2.5-flash")
            self.assertEqual(len(data["priority_order"]), 5)
            
            # 2. GET /system/gemini/stats
            response = self.client.get("/system/gemini/stats")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("success_rate", data)
            self.assertEqual(data["success_rate"]["gemini-2.5-flash"], 1.0)
            
            # 3. GET /system/gemini/health
            response = self.client.get("/system/gemini/health")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["router_status"], "healthy")
            self.assertIn("gemini-2.5-flash", data["healthy_models"])


if __name__ == "__main__":
    unittest.main()
