"""
verify_sprint_30.py — End-to-End Integration and Verification tests for Sprint 30.
"""

import os
import sys
import time
import json
import unittest
import subprocess
import hashlib
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
TEST_DB_FILE = "./verify_sprint30_temp.db"
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
from app.models.asset import Asset
from app.services.assets.asset_manager import AssetManager
from app.services.assets.asset_status import AssetStatus
from app.services import generation_job as job_service


class TestSprint30AssetRegistry(unittest.TestCase):
    """Integration and Unit verification tests for Sprint 30 Asset Registry & revision workflow."""

    def setUp(self):
        self.db = TestSessionLocal()
        
        # Setup clean test data
        self.project = Project(
            title="Sprint 30 Test Project",
            video_type=VideoType.MEDIUM,
            target_duration_seconds=60,
            aspect_ratio=AspectRatio.SIXTEEN_TO_NINE,
            language="English",
            art_style=ArtStyle.ANIME,
            narration_style=NarrationStyle.THIRD_PERSON,
            subtitle_language="English",
            voice_gender=VoiceGender.MALE
        )
        self.project.continuity_key = "con_sprint30_key"
        self.db.add(self.project)
        self.db.commit()
        self.db.refresh(self.project)

        from app.models.story import Story
        from app.models.episode import Episode
        from app.models.scene import Scene

        self.story = Story(project_id=self.project.id, title="Test Story Title", summary="A great story")
        self.db.add(self.story)
        self.db.commit()
        self.db.refresh(self.story)
        
        self.episode = Episode(story_id=self.story.id, episode_number=1, title="Test Episode Title")
        self.db.add(self.episode)
        self.db.commit()
        self.db.refresh(self.episode)
        
        self.scene = Scene(episode_id=self.episode.id, scene_number=1, title="Test Scene Title")
        self.db.add(self.scene)
        self.db.commit()
        self.db.refresh(self.scene)

        # Start FastAPI backend in the background using uvicorn
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
        print("[TearDown] Stopping backend server...")
        self.backend_process.terminate()
        self.backend_process.wait()
        
        self.db.close()
        
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass

    def test_asset_registration_and_metadata_persistence(self):
        """Task 2, 3, 6, 7 & 8: Verify asset registration, metadata, and prompt reproducibility fields."""
        spec_dict = {
            "job_id": "job_30_1",
            "provider": "huggingface",
            "model": "black-forest-labs/FLUX.1-dev",
            "compiled_positive_prompt": "A fantasy sword glowing blue in a dark forest",
            "compiled_negative_prompt": "blurry, low quality",
            "generation_parameters": {
                "width": 1024,
                "height": 576,
                "seed": 98765
            },
            "version": "2.0"
        }
        
        job = GenerationJob(
            scene_id=self.scene.id,
            shot_number=1,
            provider="flux",
            prompt=json.dumps(spec_dict),
            negative_prompt="blurry, low quality",
            status="processing",
            drive_file_id="/path/to/image.png",
            generation_time=4.5
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        # Complete the job via the service (which triggers AssetManager registration)
        completed_job = job_service.complete_job(
            db=self.db,
            job_id=job.id,
            drive_file_id="/path/to/image_final.png",
            generation_time=5.2,
            provider="huggingface"
        )
        
        self.assertIsNotNone(completed_job)
        self.assertEqual(completed_job.status, "completed")
        
        # Verify asset was registered in the database
        manager = AssetManager(self.db)
        assets = manager.list_assets(generation_job_id=job.id)
        self.assertEqual(len(assets), 1)
        
        asset = assets[0]
        self.assertEqual(asset.image_path, "/path/to/image_final.png")
        self.assertEqual(asset.generation_time, 5.2)
        self.assertEqual(asset.provider, "huggingface")
        self.assertEqual(asset.model, "black-forest-labs/FLUX.1-dev")
        self.assertEqual(asset.seed, 98765)
        self.assertEqual(asset.width, 1024)
        self.assertEqual(asset.height, 576)
        self.assertEqual(asset.compiled_positive_prompt, "A fantasy sword glowing blue in a dark forest")
        self.assertEqual(asset.compiled_negative_prompt, "blurry, low quality")
        self.assertEqual(asset.generation_spec_version, "2.0")
        self.assertEqual(asset.status, AssetStatus.GENERATED)
        
        # Verify prompt hash matches
        expected_hash = hashlib.sha256(spec_dict["compiled_positive_prompt"].encode("utf-8")).hexdigest()
        self.assertEqual(asset.prompt_hash, expected_hash)

        # Verify RenderProfile and future hooks in metadata_json (Task 7 & 9)
        self.assertIn("render_profile", asset.metadata_json)
        self.assertIn("embeddings", asset.metadata_json)
        self.assertIn("quality_score", asset.metadata_json)
        self.assertIn("similarity_score", asset.metadata_json)
        self.assertIn("character_reference_images", asset.metadata_json)
        self.assertIn("background_reference_images", asset.metadata_json)
        self.assertIn("face_consistency", asset.metadata_json)
        self.assertIn("lora_generation", asset.metadata_json)

    def test_revision_and_approval_workflow(self):
        """Task 4 & 5: Verify revision increments and approved/rejected/archive workflows."""
        spec_dict = {
            "job_id": "job_30_rev",
            "provider": "huggingface",
            "model": "black-forest-labs/FLUX.1-dev",
            "compiled_positive_prompt": "Character rendering",
            "generation_parameters": {"width": 800, "height": 600, "seed": 11111},
            "version": "1.0"
        }
        
        # Register revision 1
        job1 = GenerationJob(
            scene_id=self.scene.id,
            shot_number=3,
            prompt=json.dumps(spec_dict),
            status="completed",
            drive_file_id="/path/to/rev1.png",
            generation_time=3.5
        )
        self.db.add(job1)
        self.db.commit()
        
        manager = AssetManager(self.db)
        asset1 = manager.register_completed_job(job1)
        self.assertEqual(asset1.revision, 1)
        self.assertEqual(asset1.status, AssetStatus.GENERATED)

        # Register revision 2 for the same shot
        job2 = GenerationJob(
            scene_id=self.scene.id,
            shot_number=3,
            prompt=json.dumps(spec_dict),
            status="completed",
            drive_file_id="/path/to/rev2.png",
            generation_time=3.8
        )
        self.db.add(job2)
        self.db.commit()
        
        asset2 = manager.register_completed_job(job2)
        self.assertEqual(asset2.revision, 2)
        self.assertEqual(asset2.status, AssetStatus.GENERATED)
        
        # Approve revision 2 -> demotes revision 1 to archived
        approved_asset = manager.approve_asset(asset2.id)
        self.assertEqual(approved_asset.status, AssetStatus.APPROVED)
        
        # Refresh and check asset 1
        self.db.refresh(asset1)
        self.assertEqual(asset1.status, AssetStatus.ARCHIVED)
        
        # Verify latest vs approved query
        latest = manager.repository.get_latest_revision(project_id=self.project.id, scene_id=self.scene.id, shot_id=3)
        self.assertEqual(latest.id, asset2.id)
        
        approved = manager.repository.get_approved_revision(project_id=self.project.id, scene_id=self.scene.id, shot_id=3)
        self.assertEqual(approved.id, asset2.id)
        
        # Archive the approved asset
        archived = manager.archive_asset(asset2.id)
        self.assertEqual(archived.status, AssetStatus.ARCHIVED)
        
        # Reject revision 1
        rejected = manager.reject_asset(asset1.id)
        self.assertEqual(rejected.status, AssetStatus.REJECTED)

    def test_api_endpoints(self):
        """Task 10: Verify the new FastAPI endpoint controllers."""
        import requests
        
        # Create an asset in the DB directly
        asset = Asset(
            continuity_key="con_api_test",
            project_id=self.project.id,
            scene_id=self.scene.id,
            shot_id=1,
            asset_type="image",
            image_path="/path/to/image.png",
            storage_provider="local",
            revision=1,
            status=AssetStatus.GENERATED,
            metadata_json={}
        )
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        
        # 1. GET /assets
        res = requests.get("http://127.0.0.1:8000/assets")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(len(data) > 0)
        
        # 2. GET /assets/{id}
        res = requests.get(f"http://127.0.0.1:8000/assets/{asset.id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["image_path"], "/path/to/image.png")
        
        # 3. GET /assets/scene/{scene_id}
        res = requests.get(f"http://127.0.0.1:8000/assets/scene/{self.scene.id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)
        
        # 4. GET /assets/shot/{shot_id}
        res = requests.get("http://127.0.0.1:8000/assets/shot/1")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(res.json()) > 0)
 
        # 5. GET /assets/project/{project_id}
        res = requests.get(f"http://127.0.0.1:8000/assets/project/{self.project.id}")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(res.json()) > 0)
 
        # 6. GET /assets/continuity/{continuity_key}
        res = requests.get("http://127.0.0.1:8000/assets/continuity/con_api_test")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)
        
        # 7. POST /assets/{id}/approve
        res = requests.post(f"http://127.0.0.1:8000/assets/{asset.id}/approve")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], AssetStatus.APPROVED)
        
        # 8. POST /assets/{id}/reject
        res = requests.post(f"http://127.0.0.1:8000/assets/{asset.id}/reject")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], AssetStatus.REJECTED)
 
        # 9. POST /assets/{id}/archive
        res = requests.post(f"http://127.0.0.1:8000/assets/{asset.id}/archive")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], AssetStatus.ARCHIVED)


if __name__ == "__main__":
    unittest.main()
