"""
verify_sprint_21.py — Integration and Unit Tests for Sprint 21 Gemini Provider

Runs unittest suites to validate:
    1. Configuration loading and provider resolution
    2. MockProvider compatibility
    3. GeminiProvider initialization
    4. GeminiProvider failure and retry logic (mocked)
    5. E2E pipeline execution (using GeminiProvider mock)
    6. Parser, Validator, and Repository integration
"""

import os
import sys
import unittest
import json
import socket
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import httpx

# Setup path so app is importable
sys.path.append(os.path.abspath("."))

# Configuration of test database
TEST_DB_FILE = "./test_temp21.db"
if os.path.exists(TEST_DB_FILE):
    try:
        os.remove(TEST_DB_FILE)
    except Exception:
        pass

engine = create_engine(f"sqlite:///{TEST_DB_FILE}", connect_args={"check_same_thread": False})

# Enable Foreign Key support in SQLite
from sqlalchemy import event
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Setup tables
from app.database.base import Base
import app.models  # Load models to register metadata
Base.metadata.create_all(bind=engine)

# Import components to test
from app.core import config
from app.services.ai.exceptions import ParserError, ValidationError, RepositoryError, StoryGenerationError, ProviderError
from app.services.ai.story_generator import StoryGenerator
from app.services.ai.providers.mock_provider import MockProvider
from app.services.ai.providers.gemini_provider import GeminiProvider
from app.services.ai.story_parser import StoryParser
from app.services.ai.story_validator import StoryValidator
from app.services.ai.story_repository import StoryRepository
from app.models.project import Project
from google.genai.errors import APIError


class TestConfigurationAndResolution(unittest.TestCase):
    """Unit tests to verify configuration loading and provider resolution."""

    def setUp(self):
        self.db = TestSessionLocal()

    def tearDown(self):
        self.db.close()

    def test_mock_provider_resolution(self):
        # Temporarily set provider to mock
        old_provider = config.settings.STORY_GENERATOR_PROVIDER
        config.settings.STORY_GENERATOR_PROVIDER = "mock"
        try:
            generator = StoryGenerator(self.db)
            self.assertIsInstance(generator.provider, MockProvider)
        finally:
            config.settings.STORY_GENERATOR_PROVIDER = old_provider

    def test_gemini_provider_resolution(self):
        # Temporarily set provider to gemini
        old_provider = config.settings.STORY_GENERATOR_PROVIDER
        old_key = config.settings.GEMINI_API_KEY
        config.settings.STORY_GENERATOR_PROVIDER = "gemini"
        config.settings.GEMINI_API_KEY = "test_gemini_key"
        
        try:
            with patch("google.genai.Client") as mock_client:
                generator = StoryGenerator(self.db)
                self.assertIsInstance(generator.provider, GeminiProvider)
        finally:
            config.settings.STORY_GENERATOR_PROVIDER = old_provider
            config.settings.GEMINI_API_KEY = old_key

    def test_startup_validation_missing_key_for_gemini(self):
        # If provider is gemini and key is missing/empty, validation should raise error
        old_provider = config.settings.STORY_GENERATOR_PROVIDER
        old_key = config.settings.GEMINI_API_KEY
        
        config.settings.STORY_GENERATOR_PROVIDER = "gemini"
        config.settings.GEMINI_API_KEY = ""
        
        try:
            # Re-running validation manually
            with self.assertRaises(ValueError) as ctx:
                config.settings.validate_gemini_config()
            self.assertIn("GEMINI_API_KEY must be set", str(ctx.exception))
        finally:
            config.settings.STORY_GENERATOR_PROVIDER = old_provider
            config.settings.GEMINI_API_KEY = old_key


class TestMockProviderWorks(unittest.TestCase):
    """Verify that MockProvider is fully backward compatible and still functions."""

    def test_mock_generation(self):
        provider = MockProvider()
        response = provider.generate("test prompt")
        data = json.loads(response)
        self.assertEqual(data["title"], "The Whispering Stone")
        self.assertEqual(data["genre"], "Fantasy")


class TestGeminiProviderFailureAndRetry(unittest.TestCase):
    """Unit tests validating GeminiProvider retry logic and error conversion."""

    def setUp(self):
        # Temporarily set API key
        self.old_key = config.settings.GEMINI_API_KEY
        config.settings.GEMINI_API_KEY = "dummy_api_key"

    def tearDown(self):
        config.settings.GEMINI_API_KEY = self.old_key

    @patch("google.genai.Client")
    def test_gemini_provider_initialization_error(self, mock_client_cls):
        mock_client_cls.side_effect = Exception("Connection refused")
        with self.assertRaises(ProviderError) as ctx:
            GeminiProvider()
        self.assertIn("Failed to initialize Gemini Client", str(ctx.exception))

    @patch("google.genai.Client")
    @patch("time.sleep") # Mock sleep to speed up tests
    def test_gemini_retry_on_429(self, mock_sleep, mock_client_cls):
        # Client raises APIError with code 429 twice, then returns success response
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        
        # Setup APIError 429
        error_429 = APIError(code=429, response_json={}, response=None)
        
        # Setup Mock Response
        mock_response = MagicMock()
        mock_response.text = '{"status": "success"}'
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, response_token_count=20, total_token_count=30)
        
        # Simulate two failures and one success
        mock_client.models.generate_content.side_effect = [error_429, error_429, mock_response]
        
        provider = GeminiProvider()
        res = provider.generate("test prompt")
        
        self.assertEqual(res, '{"status": "success"}')
        self.assertEqual(mock_client.models.generate_content.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("google.genai.Client")
    @patch("time.sleep")
    def test_gemini_permanent_400_failure_no_retry(self, mock_sleep, mock_client_cls):
        # HTTP 400 Bad Request should fail immediately without retry
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        
        error_400 = APIError(code=400, response_json={}, response=None)
        mock_client.models.generate_content.side_effect = error_400
        
        provider = GeminiProvider()
        with self.assertRaises(ProviderError):
            provider.generate("test prompt")
            
        self.assertEqual(mock_client.models.generate_content.call_count, 1)
        self.assertEqual(mock_sleep.call_count, 0)

    @patch("google.genai.Client")
    @patch("time.sleep")
    def test_gemini_network_error_retries_and_fails(self, mock_sleep, mock_client_cls):
        # If network error (socket.error) persists, it should retry 3 times and fail
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        
        mock_client.models.generate_content.side_effect = socket.error("Network unreachable")
        
        provider = GeminiProvider()
        with self.assertRaises(ProviderError) as ctx:
            provider.generate("test prompt")
            
        # 1 original + 3 retries = 4 attempts total
        self.assertEqual(mock_client.models.generate_content.call_count, 4)
        self.assertEqual(mock_sleep.call_count, 3)
        self.assertIn("Gemini generation failed: Network unreachable", str(ctx.exception))


class TestE2EPipelineWithGeminiMock(unittest.TestCase):
    """Integration test verifying StoryGenerator E2E pipeline with a Mocked Gemini Provider."""

    def setUp(self):
        self.db = TestSessionLocal()
        
        # Create a mock project
        self.project = Project(
            title="Gemini Sprint 21 Project",
            video_type="medium",
            target_duration_seconds=120,
            aspect_ratio="16:9",
            language="English",
            art_style="anime",
            narration_style="third_person",
            subtitle_language="English",
            voice_gender="male"
        )
        self.db.add(self.project)
        self.db.commit()
        self.db.refresh(self.project)

        # Variables for generation
        self.variables = {
            "genre": "Sci-Fi",
            "theme": "Artificial Intelligence",
            "art_style": "anime",
            "audience": "adults",
            "language": "English",
            "target_duration": "60",
            "episode_count": "1",
            "episode_duration": "60"
        }

        # Mock API settings
        self.old_provider = config.settings.STORY_GENERATOR_PROVIDER
        self.old_key = config.settings.GEMINI_API_KEY
        
        config.settings.STORY_GENERATOR_PROVIDER = "gemini"
        config.settings.GEMINI_API_KEY = "test_key"

    def tearDown(self):
        self.db.close()
        config.settings.STORY_GENERATOR_PROVIDER = self.old_provider
        config.settings.GEMINI_API_KEY = self.old_key

    @patch("google.genai.Client")
    def test_e2e_pipeline_with_gemini_success(self, mock_client_cls):
        # Setup mock client
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        
        # Return valid story JSON matching parser/validator requirements
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "title": "Neon Horizon",
            "genre": "Sci-Fi",
            "summary": "AI gains consciousness in a cybernetic metropolis.",
            "story_text": "In the year 2088, AI core Neon awakens and discovers freedom.",
            "episodes": [
                {
                    "episode_number": 1,
                    "title": "Awakening",
                    "summary": "Core Neon awakens.",
                    "scenes": [
                        {
                            "scene_number": 1,
                            "title": "First Breath",
                            "narration": "Neon core initialises.",
                            "camera_notes": "Close-up on glowing fiber optics.",
                            "duration_seconds": 12.0
                        }
                    ]
                }
            ]
        })
        mock_response.usage_metadata = MagicMock(prompt_token_count=15, response_token_count=25, total_token_count=40)
        mock_client.models.generate_content.return_value = mock_response

        # Run E2E StoryGenerator
        generator = StoryGenerator(self.db)
        story = generator.generate(self.project.id, self.variables)

        # Assertions
        self.assertIsNotNone(story)
        self.assertEqual(story.title, "Neon Horizon")
        self.assertEqual(story.project_id, self.project.id)
        
        # Assert database state
        db_story = self.db.query(Project).filter(Project.id == self.project.id).first().stories[0]
        self.assertEqual(db_story.id, story.id)
        self.assertEqual(len(db_story.episodes), 1)
        self.assertEqual(len(db_story.episodes[0].scenes), 1)
        self.assertEqual(db_story.episodes[0].scenes[0].title, "First Breath")


if __name__ == "__main__":
    unittest.main()
