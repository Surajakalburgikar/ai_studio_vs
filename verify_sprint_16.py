import os
import sys
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup paths
sys.path.append(os.path.abspath("."))

TEST_DB_FILE = "./test_temp16.db"
if os.path.exists(TEST_DB_FILE):
    os.remove(TEST_DB_FILE)

engine = create_engine(f"sqlite:///{TEST_DB_FILE}", connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Register models
from app.database.base import Base
import app.models

Base.metadata.create_all(bind=engine)

from app.main import app
from app.database.session import get_db

def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

class Sprint16RegressionTests(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Create a test project: duration = 600 seconds (10 minutes)
        proj_payload = {
            "title": "Sprint 16 Production Plan Project",
            "description": "Integration testing for Production Planner",
            "video_type": "medium",
            "target_duration_seconds": 600,
            "aspect_ratio": "16:9",
            "language": "English",
            "art_style": "anime",
            "narration_style": "third_person",
            "subtitle_language": "English",
            "voice_gender": "male"
        }
        res = client.post("/projects", json=proj_payload)
        assert res.status_code == 201, res.text
        cls.project_id = res.json()["id"]

    def test_01_get_default_plan(self):
        """Verify GET /projects/{project_id}/production-plan returns a default calculated plan."""
        res = client.get(f"/projects/{self.project_id}/production-plan")
        self.assertEqual(res.status_code, 200)
        
        data = res.json()
        self.assertEqual(data["project_id"], self.project_id)
        self.assertEqual(data["animation_profile"], "standard")
        self.assertEqual(data["production_profile"], "long_form")
        self.assertEqual(data["quality_profile"], "standard")
        
        # Calculate expected estimates for:
        # duration = 600 seconds
        # long_form average scene duration = 15.0 seconds
        # estimated_scenes = 600 / 15 = 40 scenes
        # standard shots per scene = 4 -> 160 shots
        # standard keyframes per shot = 2 -> 320 keyframes
        # standard size per image = 1.0 MB -> 320.0 MB
        # standard render time = 2.0s per image * 1.0 multiplier -> 640 seconds -> 10.67 minutes
        # narration = 600 * 0.9 = 540 seconds
        self.assertEqual(data["target_runtime_seconds"], 600)
        self.assertEqual(data["estimated_scene_count"], 40)
        self.assertEqual(data["estimated_shot_count"], 160)
        self.assertEqual(data["estimated_keyframe_count"], 320)
        self.assertEqual(data["estimated_image_count"], 320)
        self.assertEqual(data["estimated_narration_duration"], 540.0)
        self.assertEqual(data["estimated_storage_mb"], 320.0)
        self.assertEqual(data["estimated_render_minutes"], 10.67)

    def test_02_update_plan_and_recalculate(self):
        """Verify PUT /projects/{project_id}/production-plan updates profiles and recalculates correctly."""
        # Set to: Cinema, Reel, Ultra
        update_payload = {
            "animation_profile": "cinema",
            "production_profile": "reel",
            "quality_profile": "ultra"
        }
        res = client.put(f"/projects/{self.project_id}/production-plan", json=update_payload)
        self.assertEqual(res.status_code, 200)
        
        data = res.json()
        self.assertEqual(data["animation_profile"], "cinema")
        self.assertEqual(data["production_profile"], "reel")
        self.assertEqual(data["quality_profile"], "ultra")
        
        # Calculate expected estimates for:
        # duration = 600 seconds
        # reel average scene duration = 6.0 seconds
        # estimated_scenes = 600 / 6 = 100 scenes
        # cinema shots per scene = 8 -> 800 shots
        # cinema keyframes per shot = 8 -> 6400 keyframes
        # ultra size per image = 16.0 MB -> 6400 * 16.0 = 102400.0 MB
        # cinema render time = 15.0s per image * 4.0 multiplier -> 60.0s per image
        # total render time = 6400 * 60 = 384000 seconds -> 6400.0 minutes
        # narration = 600 * 0.9 = 540.0 seconds
        self.assertEqual(data["estimated_scene_count"], 100)
        self.assertEqual(data["estimated_shot_count"], 800)
        self.assertEqual(data["estimated_keyframe_count"], 6400)
        self.assertEqual(data["estimated_image_count"], 6400)
        self.assertEqual(data["estimated_storage_mb"], 102400.0)
        self.assertEqual(data["estimated_render_minutes"], 6400.0)

    def test_03_get_plan_returns_saved(self):
        """Verify GET returns the updated/saved production plan from database."""
        res = client.get(f"/projects/{self.project_id}/production-plan")
        self.assertEqual(res.status_code, 200)
        
        data = res.json()
        self.assertEqual(data["animation_profile"], "cinema")
        self.assertEqual(data["production_profile"], "reel")
        self.assertEqual(data["quality_profile"], "ultra")
        self.assertEqual(data["estimated_scene_count"], 100)

    def test_04_nonexistent_project_returns_404(self):
        """Verify GET and PUT return 404 for nonexistent projects."""
        res_get = client.get("/projects/99999/production-plan")
        self.assertEqual(res_get.status_code, 404)
        
        update_payload = {
            "animation_profile": "basic",
            "production_profile": "shorts",
            "quality_profile": "draft"
        }
        res_put = client.put("/projects/99999/production-plan", json=update_payload)
        self.assertEqual(res_put.status_code, 404)

    @classmethod
    def tearDownClass(cls):
        engine.dispose()
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass

if __name__ == "__main__":
    unittest.main()
