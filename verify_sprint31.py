"""
verify_sprint31.py — Integration and Verification tests for Sprint 31.
"""

import os
os.environ["IMAGE_PROVIDER"] = "mock"
os.environ["VERIFY_PIPELINE"] = "true"
import sys
import time
import json
import shutil
import unittest
import subprocess
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup paths so app and worker are importable
sys.path.append(os.path.abspath("."))
sys.path.append("c:/Projects/AI_STUDIO")

# Config test database
TEST_DB_FILE = "./verify_sprint31_temp.db"
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
from app.models.story import Story
from app.models.episode import Episode
from app.models.scene import Scene
from app.models.generation_job import GenerationJob
from app.models.asset import Asset
from app.services.assets.asset_manager import AssetManager


class TestSprint31E2ESceneGeneration(unittest.TestCase):
    """Integration and verification tests for Sprint 31 E2E Scene Generation."""

    def setUp(self):
        self.db = TestSessionLocal()

        # Clean generated folders before starting
        for p in ["./generated", "../AI_STUDIO_WORKER/generated"]:
            if os.path.exists(p):
                try:
                    shutil.rmtree(p)
                except Exception:
                    pass

        # Start FastAPI backend in the background using uvicorn
        print("[Setup] Starting backend server...")
        self.backend_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1"],
            cwd="c:/Projects/AI_STUDIO",
            env={
                **os.environ,
                "DATABASE_URL": f"sqlite:///{os.path.abspath(TEST_DB_FILE)}",
                "IMAGE_PROVIDER": "mock",
                "VERIFY_PIPELINE": "true"
            }
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
            raise RuntimeError("Backend server did not respond in time.")

    def tearDown(self):
        print("[TearDown] Stopping backend server...")
        self.backend_process.terminate()
        self.backend_process.wait()

        self.db.close()

        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass

        # Cleanup generated folders
        for p in ["./generated", "../AI_STUDIO_WORKER/generated"]:
            if os.path.exists(p):
                try:
                    shutil.rmtree(p)
                except Exception:
                    pass

    def test_end_to_end_project_generation(self):
        """Verify Task 1 to Task 8: Sync project generation, output layout, progress API, retry policies, and summaries."""
        import requests

        # 1. Create a project
        payload = {
            "title": "Sprint 31 E2E Test Project",
            "video_type": "medium",
            "target_duration_seconds": 60,
            "aspect_ratio": "16:9",
            "language": "English",
            "art_style": "anime",
            "narration_style": "third_person",
            "subtitle_language": "English",
            "voice_gender": "male"
        }
        res = requests.post("http://127.0.0.1:8000/projects/", json=payload)
        self.assertEqual(res.status_code, 201)
        project_data = res.json()
        project_id = project_data["id"]
        self.assertEqual(project_data["status"], "draft")

        # 2. Add story, episode, scene, storyboard details
        # Let's seed DB directly for testing pipelines.
        # Project pipeline is registered to run stages: StoryStage, SceneDirectorStage, ShotPlannerStage, etc.
        # But wait! StoryStage needs Gemini. To be resilient and run in Mode 1 (Pipeline verification)
        # without real Gemini, VERIFY_PIPELINE=true is handled in the stages.
        # Let's set VERIFY_PIPELINE=true to force MockProvider in stages!
        os.environ["VERIFY_PIPELINE"] = "true"

        # Call POST /projects/{project_id}/generate?async_mode=False to run synchronously
        print(f"[Test] Starting sync project generation for project {project_id}...")
        gen_res = requests.post(f"http://127.0.0.1:8000/projects/{project_id}/generate?async_mode=false")
        self.assertIn(gen_res.status_code, [200, 202])
        gen_data = gen_res.json()
        print(f"[Test] Generation response: {gen_data}")
        self.assertEqual(gen_data["status"], "completed")
        self.assertGreater(gen_data["total_shots"], 0)
        self.assertEqual(gen_data["completed_shots"], gen_data["total_shots"])

        # 3. Check progress status endpoint
        status_res = requests.get(f"http://127.0.0.1:8000/projects/{project_id}/generation-status")
        self.assertEqual(status_res.status_code, 200)
        status_data = status_res.json()
        self.assertEqual(status_data["status"], "completed")
        self.assertEqual(status_data["completed_scenes"], status_data["total_scenes"])
        self.assertEqual(status_data["completed_shots"], status_data["total_shots"])
        self.assertIn("mock", status_data["provider_metrics"])



        project_folder = Path(f"c:/Projects/AI_STUDIO_WORKER/generated/Project_{project_id:03d}")
        if not project_folder.exists():
            project_folder = Path(f"./generated/Project_{project_id:03d}")
        self.assertTrue(project_folder.exists())
        
        # Verify metadata.json and production_summary files
        summary_json = project_folder / "production_summary.json"
        summary_md = project_folder / "production_summary.md"
        self.assertTrue(summary_json.exists())
        self.assertTrue(summary_md.exists())

        with open(summary_json, "r") as f:
            summary_data = json.load(f)
            self.assertEqual(summary_data["project_id"], project_id)
            self.assertEqual(summary_data["total_shots"], gen_data["total_shots"])
            self.assertEqual(summary_data["completed_shots"], gen_data["total_shots"])
            self.assertEqual(len(summary_data["assets"]), gen_data["total_shots"])

        # Verify scene folder and metadata
        scene_folders = list(project_folder.glob("Scene_*"))
        self.assertGreater(len(scene_folders), 0)
        for scene_dir in scene_folders:
            metadata_file = scene_dir / "metadata.json"
            self.assertTrue(metadata_file.exists())
            with open(metadata_file, "r") as f:
                scene_meta = json.load(f)
                self.assertEqual(scene_meta["status"], "completed")
                self.assertGreater(len(scene_meta["shot_list"]), 0)
                
            # Verify that png shot images exist!
            png_files = list(scene_dir.glob("shot_*.png"))
            self.assertEqual(len(png_files), len(scene_meta["shot_list"]))

    def test_automatic_retry_and_failure_recovery(self):
        """Verify Task 5, 6, 7 & 8: Retry policies for 429 vs 401, scene and project completion on failure recovery."""
        # Seeding a manual project, story, episode, scene to test worker executor with retryable/non-retryable errors
        project = Project(
            title="Retry Test Project",
            video_type=VideoType.MEDIUM,
            target_duration_seconds=60,
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

        story = Story(project_id=project.id, title="Test Story", summary="A great story")
        self.db.add(story)
        self.db.commit()
        self.db.refresh(story)

        episode = Episode(story_id=story.id, episode_number=1, title="Test Episode")
        self.db.add(episode)
        self.db.commit()
        self.db.refresh(episode)

        scene = Scene(episode_id=episode.id, scene_number=1, title="Test Scene")
        self.db.add(scene)
        self.db.commit()
        self.db.refresh(scene)

        # Let's add 3 generation jobs:
        # Job 1: Normal generation (succeeds)
        # Job 2: Retryable error (Rate limit 429) -> Retries 3 times, then fails permanently
        # Job 3: Non-retryable error (Unauthorized 401) -> Fails immediately without retries
        job1 = GenerationJob(
            scene_id=scene.id,
            shot_number=1,
            provider="mock",
            prompt="A normal shot description",
            status="pending",
            priority=10,
            retry_count=0,
            progress=0
        )
        job2 = GenerationJob(
            scene_id=scene.id,
            shot_number=2,
            provider="mock",
            prompt="A shot trigger_rate_limit description",
            status="pending",
            priority=5,
            retry_count=0,
            progress=0
        )
        job3 = GenerationJob(
            scene_id=scene.id,
            shot_number=3,
            provider="mock",
            prompt="A shot trigger_unauthorized description",
            status="pending",
            priority=1,
            retry_count=0,
            progress=0
        )
        self.db.add_all([job1, job2, job3])
        self.db.commit()

        # Execute jobs using the process_project_jobs loop
        print("[Test] Processing jobs for retry/failure verification...")
        from app.api.projects import process_project_jobs
        
        # We need a new session in the same thread or we can pass self.db
        process_project_jobs(self.db, project.id)

        # Refresh database objects
        self.db.refresh(project)
        self.db.refresh(scene)
        self.db.refresh(job1)
        self.db.refresh(job2)
        self.db.refresh(job3)

        # Verify Job 1 succeeded
        self.assertEqual(job1.status, "completed")
        self.assertEqual(job1.progress, 100)

        # Verify Job 2 retried 3 times (reaches retry_count=3) and then failed
        self.assertEqual(job2.status, "failed")
        self.assertEqual(job2.retry_count, 3)
        self.assertIn("Rate limit 429", job2.error_message)

        # Verify Job 3 failed immediately with retry_count=0
        self.assertEqual(job3.status, "failed")
        self.assertEqual(job3.retry_count, 0)
        self.assertIn("Unauthorized 401", job3.error_message)

        # Verify Scene completed anyway (Failure Recovery!)
        self.assertEqual(scene.status, "completed")

        # Verify Project completed anyway (Failure Recovery!)
        self.assertEqual(project.status, "completed")



        # Verify project folder structure was created and contains metadata.json
        project_folder = Path(f"c:/Projects/AI_STUDIO_WORKER/generated/Project_{project.id:03d}")
        if not project_folder.exists():
            project_folder = Path(f"./generated/Project_{project.id:03d}")
        self.assertTrue(project_folder.exists())
        self.assertTrue((project_folder / "production_summary.json").exists())
        self.assertTrue((project_folder / "production_summary.md").exists())
        
        scene_folder = project_folder / f"Scene_{scene.scene_number:03d}"
        self.assertTrue(scene_folder.exists())
        self.assertTrue((scene_folder / "metadata.json").exists())
        
        # Verify shot 1 image was generated, but shots 2 and 3 were not (or failed)
        self.assertTrue((scene_folder / "shot_001.png").exists())
        self.assertFalse((scene_folder / "shot_002.png").exists())
        self.assertFalse((scene_folder / "shot_003.png").exists())


if __name__ == "__main__":
    unittest.main()
