"""
verify_sprint30_1.py — Integration and Verification tests for Sprint 30.1.
"""

import os
import sys
import time
import json
import unittest
import subprocess
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup paths so app and worker are importable
sys.path.append(os.path.abspath("."))
sys.path.append("c:/Projects/AI_STUDIO")

# Config test database
TEST_DB_FILE = "./verify_sprint30_1_temp.db"
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
from app.models.asset_collection import AssetCollection
from app.models.asset_usage import AssetUsage
from app.services.assets.asset_manager import AssetManager
from app.services.assets.asset_status import AssetStatus
from app.services.assets.asset_collection import AssetCollectionRepository
from app.services.assets.asset_tags import AssetTagManager
from app.services.assets.asset_usage import AssetUsageManager, UsagePurpose
from app.services import generation_job as job_service


class TestSprint30_1AssetManagement(unittest.TestCase):
    """Integration and Unit verification tests for Sprint 30.1."""

    def setUp(self):
        self.db = TestSessionLocal()

        # Setup clean test data
        self.project = Project(
            title="Sprint 30.1 Test Project",
            video_type=VideoType.MEDIUM,
            target_duration_seconds=60,
            aspect_ratio=AspectRatio.SIXTEEN_TO_NINE,
            language="English",
            art_style=ArtStyle.ANIME,
            narration_style=NarrationStyle.THIRD_PERSON,
            subtitle_language="English",
            voice_gender=VoiceGender.MALE
        )
        self.project.continuity_key = "con_sprint30_1"
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

    def test_asset_collections_and_revisions(self):
        """Verify asset collection auto-creation, grouping, and canonical selection."""
        # 1. Register first asset revision
        spec_dict = {
            "job_id": "job_30_1_1",
            "provider": "huggingface",
            "model": "black-forest-labs/FLUX.1-dev",
            "compiled_positive_prompt": "A beautiful castle in the forest",
            "generation_parameters": {"width": 1024, "height": 576, "seed": 101},
            "version": "1.0",
            "metadata": {"render_profile": "anime_production"}
        }
        job1 = GenerationJob(
            scene_id=self.scene.id,
            shot_number=5,
            prompt=json.dumps(spec_dict),
            status="completed",
            drive_file_id="/path/to/img1.png",
            generation_time=4.0
        )
        self.db.add(job1)
        self.db.commit()

        manager = AssetManager(self.db)
        asset1 = manager.register_completed_job(job1)

        # Verify that an AssetCollection was automatically created and linked
        self.assertIsNotNone(asset1.collection_id)
        collection_id = asset1.collection_id

        coll_repo = AssetCollectionRepository(self.db)
        coll = coll_repo.get_collection(collection_id)
        self.assertIsNotNone(coll)
        self.assertEqual(coll.project_id, self.project.id)
        self.assertEqual(coll.scene_id, self.scene.id)
        self.assertEqual(coll.shot_number, 5)
        self.assertEqual(coll.continuity_key, "con_sprint30_1")

        # 2. Register second asset revision for the same shot
        spec_dict["generation_parameters"]["seed"] = 102
        job2 = GenerationJob(
            scene_id=self.scene.id,
            shot_number=5,
            prompt=json.dumps(spec_dict),
            status="completed",
            drive_file_id="/path/to/img2.png",
            generation_time=4.2
        )
        self.db.add(job2)
        self.db.commit()

        asset2 = manager.register_completed_job(job2)

        # Verify that the second revision points to the SAME collection
        self.assertEqual(asset2.collection_id, collection_id)

        # Verify repo helper methods
        assets = coll_repo.list_assets(collection_id)
        self.assertEqual(len(assets), 2)
        self.assertEqual(assets[0].id, asset1.id)
        self.assertEqual(assets[1].id, asset2.id)

        latest = coll_repo.latest_revision(collection_id)
        self.assertEqual(latest.id, asset2.id)

        approved = coll_repo.approved_asset(collection_id)
        self.assertIsNone(approved)  # None approved yet

        # 3. Approve revision 2 and verify canonical_asset_id updates
        approved_asset = manager.approve_asset(asset2.id)
        self.assertEqual(approved_asset.status, AssetStatus.APPROVED)

        self.db.refresh(coll)
        self.assertEqual(coll.canonical_asset_id, asset2.id)

        approved = coll_repo.approved_asset(collection_id)
        self.assertEqual(approved.id, asset2.id)

        # Verify endpoint GET /assets/collection/{collection_id}
        import requests
        res = requests.get(f"http://127.0.0.1:8000/assets/collection/{collection_id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["collection_id"], collection_id)
        self.assertEqual(data["canonical_asset_id"], asset2.id)

    def test_asset_tags_and_auto_extraction(self):
        """Verify asset tag management, case-insensitivity, and auto-extraction."""
        spec_dict = {
            "job_id": "job_tags_test",
            "provider": "fal-ai",
            "model": "black-forest-labs/FLUX.1-dev",
            "compiled_positive_prompt": "A dramatic knight battle near a dark castle, close up",
            "generation_parameters": {"width": 1024, "height": 576, "seed": 777},
            "version": "1.0",
            "metadata": {"render_profile": "anime_production"}
        }
        job = GenerationJob(
            scene_id=self.scene.id,
            shot_number=8,
            prompt=json.dumps(spec_dict),
            status="completed",
            drive_file_id="/path/to/img_tags.png",
            generation_time=3.0
        )
        self.db.add(job)
        self.db.commit()

        manager = AssetManager(self.db)
        asset = manager.register_completed_job(job)

        # 1. Verify auto-extraction
        tag_mgr = AssetTagManager(self.db)
        tags = tag_mgr.list_tags(asset.id)
        
        # Checking that tags like castle, battle, dramatic, close_up, anime are present
        self.assertIn("castle", tags)
        self.assertIn("battle", tags)
        self.assertIn("dramatic", tags)
        self.assertIn("close_up", tags)
        self.assertIn("anime", tags)

        # 2. Verify add_tag, case-insensitivity, and uniqueness
        tag_mgr.add_tag(asset.id, "Forest")
        tags_after_add = tag_mgr.list_tags(asset.id)
        self.assertIn("Forest", tags_after_add)

        # Adding same tag with different casing should not result in duplicates
        tag_mgr.add_tag(asset.id, "forest")
        tag_mgr.add_tag(asset.id, "FOREST")
        self.assertEqual(len(tag_mgr.list_tags(asset.id)), len(tags_after_add))

        # 3. Verify replace_tags
        tag_mgr.replace_tags(asset.id, ["sword", "shield", "Sword"])
        replaced_tags = tag_mgr.list_tags(asset.id)
        self.assertEqual(len(replaced_tags), 2)
        self.assertIn("sword", replaced_tags)
        self.assertIn("shield", replaced_tags)

        # 4. Verify search_by_tag
        matched_assets = tag_mgr.search_by_tag("SWORD")
        self.assertEqual(len(matched_assets), 1)
        self.assertEqual(matched_assets[0].id, asset.id)

        # 5. Verify REST API Tag Endpoints
        import requests
        
        # GET /assets/tag/{tag}
        res = requests.get("http://127.0.0.1:8000/assets/tag/shield")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)

        # POST /assets/{id}/tags
        res = requests.post(f"http://127.0.0.1:8000/assets/{asset.id}/tags", json={"tags": ["magic", "dragon"]})
        self.assertEqual(res.status_code, 200)
        updated_tags = res.json()["tags"]
        self.assertIn("magic", updated_tags)
        self.assertIn("dragon", updated_tags)

        # DELETE /assets/{id}/tags/{tag}
        res = requests.delete(f"http://127.0.0.1:8000/assets/{asset.id}/tags/magic")
        self.assertEqual(res.status_code, 200)
        tags_final = tag_mgr.list_tags(asset.id)
        self.assertNotIn("magic", tags_final)

    def test_asset_usage_and_safe_deletion(self):
        """Verify asset usage tracking and deletion safety checks."""
        spec_dict = {
            "job_id": "job_usage_test",
            "provider": "fal-ai",
            "model": "black-forest-labs/FLUX.1-dev",
            "compiled_positive_prompt": "Background landscape",
            "generation_parameters": {"width": 1024, "height": 576, "seed": 999},
            "version": "1.0",
            "metadata": {"render_profile": "anime_production"}
        }
        job = GenerationJob(
            scene_id=self.scene.id,
            shot_number=12,
            prompt=json.dumps(spec_dict),
            status="completed",
            drive_file_id="/path/to/img_usage.png",
            generation_time=2.5
        )
        self.db.add(job)
        self.db.commit()

        manager = AssetManager(self.db)
        asset = manager.register_completed_job(job)

        usage_mgr = AssetUsageManager(self.db)
        self.assertTrue(usage_mgr.is_safe_to_delete(asset.id))

        # 1. Register usages
        usage1 = usage_mgr.register_usage(
            asset_id=asset.id,
            project_id=self.project.id,
            episode_id=self.episode.id,
            scene_id=self.scene.id,
            purpose=UsagePurpose.VIDEO,
            reference_id="ref_clip_1",
            metadata={"timeline_position": 15.5}
        )
        self.assertIsNotNone(usage1)
        self.assertEqual(usage1.purpose, "VIDEO")

        self.assertFalse(usage_mgr.is_safe_to_delete(asset.id))
        self.assertEqual(usage_mgr.count_usage(asset.id), 1)

        # Register second usage
        usage2 = usage_mgr.register_usage(
            asset_id=asset.id,
            project_id=self.project.id,
            episode_id=self.episode.id,
            scene_id=self.scene.id,
            purpose=UsagePurpose.TRAILER,
            reference_id="ref_clip_2"
        )
        self.assertEqual(usage_mgr.count_usage(asset.id), 2)

        # 2. Verify Deletion Safety (safe_delete)
        # Attempt safe deletion without force -> should raise ValueError
        with self.assertRaises(ValueError):
            manager.safe_delete(asset.id, force=False)

        # Verify DB still has the asset
        self.assertIsNotNone(manager.get_asset(asset.id))

        # 3. Verify REST API Usage and Safe Delete Endpoints
        import requests

        # GET /assets/{id}/usage
        res = requests.get(f"http://127.0.0.1:8000/assets/{asset.id}/usage")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 2)

        # DELETE /assets/{id}/usage/{usage_id}
        res = requests.delete(f"http://127.0.0.1:8000/assets/{asset.id}/usage/{usage1.usage_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(usage_mgr.count_usage(asset.id), 1)

        # Register new usage via API POST /assets/{id}/usage
        res = requests.post(f"http://127.0.0.1:8000/assets/{asset.id}/usage", json={
            "project_id": self.project.id,
            "purpose": "THUMBNAIL",
            "reference_id": "thumb_1"
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(usage_mgr.count_usage(asset.id), 2)

        # POST /assets/{id}/safe-delete without force -> 400 Bad Request
        res = requests.post(f"http://127.0.0.1:8000/assets/{asset.id}/safe-delete")
        self.assertEqual(res.status_code, 400)
        self.assertIn("cannot be safely deleted", res.json()["detail"])

        # POST /assets/{id}/safe-delete WITH force -> 200 OK
        res = requests.post(f"http://127.0.0.1:8000/assets/{asset.id}/safe-delete?force=true")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "success")

        # Verify asset is deleted from the database
        self.assertIsNone(manager.get_asset(asset.id))


if __name__ == "__main__":
    unittest.main()
