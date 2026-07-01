"""
verify_sprint_28.py — End-to-End Integration and Verification tests for Sprint 28.
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
TEST_DB_FILE = "./test_temp28.db"
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
from app.models.generation_job import GenerationJob
from app.services.ai.pipeline.project_pipeline import ProjectPipeline
from app.services.ai.pipeline.pipeline_context import PipelineContext
from app.services.ai.stages.job_builder_stage import JobBuilderStage

# Import worker components
from worker.jobs.fetch import JobFetcher
from worker.jobs.process import JobProcessor


def mock_text_to_image(*args, **kwargs):
    """Mock Hugging Face text_to_image call to return a red PIL image."""
    print("[Mock HF] text_to_image called. Generating red placeholder image...")
    # Use dimensions if passed
    width = kwargs.get("width", 1024)
    height = kwargs.get("height", 576)
    img = Image.new("RGB", (width, height), color=(230, 50, 50))
    return img


class TestSprint28EndToEnd(unittest.TestCase):
    """End-to-End integration test for Sprint 28 image generation flow."""

    def setUp(self):
        self.db = TestSessionLocal()
        
        # 1. Create and seed the project
        self.project = Project(
            title="Sprint 28 Test Project",
            video_type=VideoType.MEDIUM,
            target_duration_seconds=60,
            aspect_ratio=AspectRatio.SIXTEEN_TO_NINE,
            language="English",
            art_style=ArtStyle.ANIME,
            narration_style=NarrationStyle.THIRD_PERSON,
            subtitle_language="English",
            voice_gender=VoiceGender.MALE
        )
        # Seed dynamic properties for spec builder
        self.project.provider = "flux"
        self.project.model = "black-forest-labs/FLUX.1-dev"
        self.project.generation_steps = 28
        self.project.guidance_scale = 6.5
        self.project.seed = 12345
        
        self.db.add(self.project)
        self.db.commit()
        self.db.refresh(self.project)

        # 2. Start Backend FastAPI Server in the background using uvicorn
        # Set database env to our test db
        print("[Setup] Starting backend server...")
        self.backend_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1"],
            cwd="c:/Projects/AI_STUDIO",
            env={**os.environ, "DATABASE_URL": f"sqlite:///{os.path.abspath(TEST_DB_FILE)}"}
        )
        # Retry loop to wait for server readiness
        import requests
        server_ready = False
        for i in range(40):
            try:
                res = requests.get("http://127.0.0.1:8000/", timeout=1)
                if res.status_code == 200:
                    print(f"[Setup] Backend server is ready after {i*0.25} seconds.")
                    server_ready = True
                    break
            except Exception:
                pass
            time.sleep(0.25)
            
        if not server_ready:
            print("[Warning] Backend server did not respond in time.")

    def tearDown(self):
        # 1. Shutdown Backend Server
        print("[TearDown] Stopping backend server...")
        self.backend_process.terminate()
        self.backend_process.wait()
        
        self.db.close()
        
        # 2. Cleanup database file
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass

    @patch("huggingface_hub.InferenceClient.text_to_image", side_effect=mock_text_to_image)
    def test_complete_e2e_flow(self, mock_hf):
        """Verify the complete E2E pipeline generates and reports image generation correctly."""
        # 1. Execute Backend Pipeline to produce GenerationSpecification & GenerationJob
        # We run the pipeline stages
        pipeline = ProjectPipeline(self.db)
        
        # We need a Story and Scenes to process. StoryStage generates them automatically.
        variables = {
            "genre": "Fantasy",
            "theme": "Magic Sword",
            "art_style": "anime",
            "audience": "kids",
            "language": "English",
            "target_duration": "60",
            "episode_count": "1",
            "episode_duration": "60"
        }
        
        print("[E2E] Running backend pipeline...")
        summary = pipeline.generate_project(self.project.id, variables)
        self.assertEqual(summary.status, "completed")
        self.assertTrue(summary.job_count > 0)

        # 2. Verify GenerationJob in the DB contains spec JSON
        job_db = self.db.query(GenerationJob).filter(GenerationJob.status == "pending").first()
        self.assertIsNotNone(job_db)
        self.assertEqual(job_db.provider, "flux")
        
        # Try to parse spec
        spec_dict = json.loads(job_db.prompt)
        self.assertEqual(spec_dict["provider"], "flux")
        self.assertEqual(spec_dict["model"].lower(), "black-forest-labs/flux.1-dev")
        self.assertTrue(len(spec_dict["compiled_positive_prompt"]) > 0)
        self.assertEqual(spec_dict["generation_parameters"]["seed"], 12345)
        self.assertEqual(spec_dict["generation_parameters"]["width"], 1024)
        self.assertEqual(spec_dict["generation_parameters"]["height"], 576)

        # 3. Simulate Worker Polling & Execution
        print("[E2E] Simulating worker fetch and process...")
        fetcher = JobFetcher()
        processor = JobProcessor()
        
        # Set worker environment variables
        os.environ["BACKEND_URL"] = "http://localhost:8000"
        os.environ["IMAGE_PROVIDER"] = "flux"
        os.environ["STORAGE_PROVIDER"] = "local"
        
        # Fetch job (calls backend endpoint /jobs/next)
        worker_job = fetcher.fetch_job()
        self.assertIsNotNone(worker_job)
        self.assertEqual(worker_job.id, job_db.id)
        
        # Process job (executes, calls HF mock, saves locally, calls backend callbacks)
        result = processor.process(worker_job)
        self.assertTrue(result.success)
        self.assertTrue(result.provider.startswith("flux"))
        self.assertTrue(result.generation_time > 0)
        self.assertTrue(os.path.exists(result.image_path))
        print(f"[E2E] Generated image path: {result.image_path}")

        # 4. Verify reported state on the Backend DB
        self.db.expire_all()
        updated_job = self.db.query(GenerationJob).filter(GenerationJob.id == job_db.id).first()
        self.assertEqual(updated_job.status, "completed")
        self.assertEqual(updated_job.progress, 100)
        self.assertEqual(updated_job.drive_file_id, result.image_path)
        self.assertIsNotNone(updated_job.generation_time)
        self.assertTrue(updated_job.generation_time > 0)
        print("[E2E] Verification completed successfully. All assertions passed!")


if __name__ == "__main__":
    unittest.main()
