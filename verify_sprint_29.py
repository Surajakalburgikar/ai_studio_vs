"""
verify_sprint_29.py — End-to-End Integration and Verification tests for Sprint 29.
"""

import os
import sys
import time
import json
import unittest
import subprocess
from unittest.mock import patch
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup paths so app and worker are importable
sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath("../AI_STUDIO_WORKER"))
sys.path.append("c:/Projects/AI_STUDIO")
sys.path.append("c:/Projects/AI_STUDIO_WORKER")

# Config test database
TEST_DB_FILE = "./verify_sprint29_temp.db"
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

# Import components
from app.models.project import Project, VideoType, AspectRatio, ArtStyle, NarrationStyle, VoiceGender
from app.models.character import Character
from app.models.generation_job import GenerationJob
from app.services.ai.pipeline.project_pipeline import ProjectPipeline
from app.services.ai.pipeline.pipeline_context import PipelineContext
from app.services.ai.stages.job_builder_stage import JobBuilderStage

# Import continuity components
from app.services.ai.continuity.continuity_manifest import ContinuityManifest
from app.services.ai.continuity.continuity_manager import ContinuityManager
from app.services.ai.continuity.continuity_resolver import ContinuityResolver

# Import orchestrator & policies
from app.services.ai.orchestrator.production_orchestrator import ProductionOrchestrator
from app.services.ai.orchestrator.production_checkpoint import ProductionCheckpoint
from app.services.ai.policies.quality_mode import QualityMode
from app.services.ai.policies.provider_policy import ProviderPolicy

# Import worker components
from worker.jobs.fetch import JobFetcher
from worker.jobs.process import JobProcessor


def mock_text_to_image(*args, **kwargs):
    """Mock Hugging Face text_to_image call to return a red PIL image."""
    print("[Mock HF] text_to_image called.")
    img = Image.new("RGB", (1024, 576), color=(0, 200, 100))
    return img


class TestSprint29ContinuityAndOrchestration(unittest.TestCase):
    """Integration and Unit verification tests for Sprint 29 Continuity & Orchestrator."""

    def setUp(self):
        self.db = TestSessionLocal()
        
        # Ensure clean continuity folder
        self.continuity_path = "./verify_continuity_sprint29"
        os.makedirs(self.continuity_path, exist_ok=True)
        os.environ["CONTINUITY_EXPORT_PATH"] = self.continuity_path

        # Create Project
        self.project = Project(
            title="Sprint 29 Test Series Part 1",
            video_type=VideoType.MEDIUM,
            target_duration_seconds=60,
            aspect_ratio=AspectRatio.SIXTEEN_TO_NINE,
            language="English",
            art_style=ArtStyle.ANIME,
            narration_style=NarrationStyle.THIRD_PERSON,
            subtitle_language="English",
            voice_gender=VoiceGender.MALE
        )
        self.project.provider = "flux"
        self.project.model = "black-forest-labs/FLUX.1-dev"
        self.project.generation_steps = 28
        self.project.guidance_scale = 6.5
        self.project.seed = 42

        self.db.add(self.project)
        self.db.commit()
        self.db.refresh(self.project)

    def tearDown(self):
        self.db.close()
        # Cleanup continuity folder
        if os.path.exists(self.continuity_path):
            import shutil
            shutil.rmtree(self.continuity_path, ignore_errors=True)
        # Cleanup test db
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass

    def test_continuity_manifest_serialization(self):
        """Task 1: Verify ContinuityManifest properties save, load, and serialize cleanly."""
        manager = ContinuityManager()
        manifest = manager.create_new_manifest(
            continuity_key="con_test123",
            series_title="Test Series",
            universe_title="Test Universe"
        )
        
        char = {
            "name": "Alice",
            "description": "Alice in Wonderland",
            "hair_style": "long ponytail",
            "hair_color": "blonde",
            "eye_color": "blue",
            "clothing": "blue dress"
        }
        manifest.canonical_characters["alice"] = char
        
        manifest.canonical_facts.append("The sword glows blue near monsters.")

        manager.save_manifest(manifest)
        
        loaded = manager.load_manifest("con_test123")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.series_title, "Test Series")
        self.assertEqual(loaded.canonical_characters["alice"]["hair_style"], "long ponytail")
        self.assertEqual(loaded.canonical_facts[0], "The sword glows blue near monsters.")

    def test_production_orchestrator_lifecycle(self):
        """Task 2: Verify ProductionOrchestrator runs start, pause, resume, and continue flows."""
        orchestrator = ProductionOrchestrator(self.db)
        
        # 1. Start
        run = orchestrator.start_production(self.project.id)
        self.assertEqual(run.status, "active")
        self.assertIsNotNone(run.checkpoint)
        
        # Verify continuity key was populated
        self.db.refresh(self.project)
        self.assertIsNotNone(self.project.continuity_key)
        key = self.project.continuity_key
        
        # 2. Pause
        run = orchestrator.pause_production(key, reason="quality check needed")
        self.assertEqual(run.status, "paused")
        self.assertEqual(run.metadata["pause_reason"], "quality check needed")
        
        # 3. Resume
        run = orchestrator.resume_production(key)
        self.assertEqual(run.status, "active")
        
        # 4. Continue into sequel (Part 2)
        project_part2 = Project(
            title="Sprint 29 Test Series Part 2",
            video_type=VideoType.MEDIUM,
            target_duration_seconds=60,
            aspect_ratio=AspectRatio.SIXTEEN_TO_NINE,
            language="English",
            art_style=ArtStyle.ANIME,
            narration_style=NarrationStyle.THIRD_PERSON,
            subtitle_language="English",
            voice_gender=VoiceGender.MALE
        )
        self.db.add(project_part2)
        self.db.commit()
        self.db.refresh(project_part2)
        
        run_part2 = orchestrator.continue_as_new_project(self.project.id, project_part2.id)
        self.assertEqual(run_part2.status, "active")
        self.db.refresh(project_part2)
        # Sprint 29.1: continuity_key is SHARED — no _v suffix clone, just a revision entry
        self.assertEqual(project_part2.continuity_key, key,
                         "Both projects must share the same continuity_key")
        # A revision entry must have been appended recording the continuation
        mgr = ContinuityManager()
        revisions = mgr.list_revisions(key)
        self.assertTrue(len(revisions) >= 1, "A revision entry must have been appended for the sequel")

    def test_quality_preserving_provider_policy(self):
        """Task 3 & 4: Verify ProviderPolicy handles quality modes and forbids downgrades in production."""
        # 1. Production Mode: forbid downgrade
        policy_prod = ProviderPolicy(
            mode=QualityMode.PRODUCTION,
            allow_quality_downgrade=False,
            preferred_model="black-forest-labs/flux.1-dev",
            preferred_transport="fal-ai"
        )
        available = {
            "black-forest-labs/flux.1-dev": ["fal-ai", "huggingface"],
            "black-forest-labs/flux.1-schnell": ["huggingface"]
        }
        
        # Exact match available
        model, provider, action = policy_prod.select_route("black-forest-labs/flux.1-dev", "fal-ai", available)
        self.assertEqual(model, "black-forest-labs/flux.1-dev")
        self.assertEqual(provider, "fal-ai")
        self.assertEqual(action, "execute")

        # Transport fallback (same model) is allowed
        available_only_hf = {
            "black-forest-labs/flux.1-dev": ["huggingface"]
        }
        model, provider, action = policy_prod.select_route("black-forest-labs/flux.1-dev", "unsupported-transport", available_only_hf)
        self.assertEqual(model, "black-forest-labs/flux.1-dev")
        self.assertEqual(provider, "huggingface") # fallback transport
        self.assertEqual(action, "execute")

        # Model downgrade NOT allowed in production
        available_only_schnell = {
            "black-forest-labs/flux.1-schnell": ["huggingface"]
        }
        _, _, action = policy_prod.select_route("black-forest-labs/flux.1-dev", "fal-ai", available_only_schnell)
        self.assertEqual(action, "fail")

        # 2. Development Mode: allow downgrade if permitted
        policy_dev = ProviderPolicy(
            mode=QualityMode.DEVELOPMENT,
            allow_quality_downgrade=True,
            preferred_model="black-forest-labs/flux.1-dev",
            preferred_transport="fal-ai"
        )
        model, provider, action = policy_dev.select_route("black-forest-labs/flux.1-dev", "fal-ai", available_only_schnell)
        self.assertEqual(model, "black-forest-labs/flux.1-schnell")
        self.assertEqual(provider, "huggingface")
        self.assertEqual(action, "execute")

    def test_continuity_resolver_characters(self):
        """Task 5: Verify ContinuityResolver resolves visual states of character profiles."""
        manifest = ContinuityManifest(continuity_key="con_test")
        manifest.canonical_characters["bob"] = {
            "name": "Bob",
            "description": "Tall guy",
            "hair_style": "short crop",
            "hair_color": "black",
            "eye_color": "brown"
        }
        
        resolver = ContinuityResolver()
        
        # Test character resolution
        chars = [{"name": "bob", "description": "some guy"}]
        resolved = resolver.resolve_characters(manifest, chars)
        self.assertEqual(resolved[0]["hair_style"], "short crop")
        self.assertEqual(resolved[0]["hair_color"], "black")
        self.assertEqual(resolved[0]["eye_color"], "brown")

    @patch("huggingface_hub.InferenceClient.text_to_image", side_effect=mock_text_to_image)
    def test_worker_respects_policy_and_reports_details(self, mock_hf):
        """Task 7: Verify worker uses exact model + transport and reports them in ExecutionResult."""
        # Setup Job
        spec_payload = {
            "job_id": "job_123",
            "provider": "huggingface",
            "model": "black-forest-labs/FLUX.1-dev",
            "compiled_positive_prompt": "A beautiful scenery of a sunset.",
            "compiled_negative_prompt": "",
            "generation_parameters": {"width": 1024, "height": 576},
            "output_configuration": {"filename": "scenery.png"},
            "storage_configuration": {"relative_output_path": "verify_output", "filename": "scenery.png"},
            "version": "1.0",
            "metadata": {"quality_mode": "production", "allow_quality_downgrade": False}
        }
        
        job = GenerationJob(
            scene_id=1,
            shot_number=1,
            provider="flux",
            prompt=json.dumps(spec_payload),
            filename="scenery.png",
            status="pending"
        )
        
        processor = JobProcessor()
        
        # Override environment variables for the test client
        os.environ["HF_TOKEN"] = "mock-token"
        
        result = processor.process(job)
        self.assertTrue(result.success)
        # Check reported transport & model in the result
        self.assertIn("flux (huggingface:black-forest-labs/FLUX.1-dev)", result.provider)
        self.assertTrue(os.path.exists(result.image_path))
        
        # Clean up generated image
        if os.path.exists(result.image_path):
            os.remove(result.image_path)


if __name__ == "__main__":
    unittest.main()
