import os
import sys
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup paths
sys.path.append(os.path.abspath("."))

TEST_DB_FILE = "./test_temp17.db"
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

class Sprint17RegressionTests(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # 1. Create a project
        proj_payload = {
            "title": "Sprint 17 Scene Director Project",
            "description": "Integration testing for Scene Director",
            "video_type": "medium",
            "target_duration_seconds": 180,
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
        
        # 2. Create story
        story_payload = {
            "title": "Story 17",
            "genre": "Sci-Fi",
            "summary": "Testing sprint 17 scene direction"
        }
        res = client.post(f"/projects/{cls.project_id}/stories", json=story_payload)
        assert res.status_code == 201, res.text
        cls.story_id = res.json()["id"]
        
        # 3. Create episode
        episode_payload = {
            "episode_number": 1,
            "title": "Episode 17"
        }
        res = client.post(f"/stories/{cls.story_id}/episodes", json=episode_payload)
        assert res.status_code == 201, res.text
        cls.episode_id = res.json()["id"]
        
        # 4. Create scene
        scene_payload = {
            "scene_number": 1,
            "title": "Scene 17 Outer Space",
            "narration": "In the cold depth of space...",
            "camera_notes": "Follow space ship",
            "duration_seconds": 12.0
        }
        res = client.post(f"/episodes/{cls.episode_id}/scenes", json=scene_payload)
        assert res.status_code == 201, res.text
        cls.scene_id = res.json()["id"]
        
        # 5. Create character
        char_payload = {
            "name": "Captain-17",
            "role": "Pilot",
            "gender": "Female",
            "description": "Starship commander"
        }
        res = client.post(f"/stories/{cls.story_id}/characters", json=char_payload)
        assert res.status_code == 201, res.text
        cls.character_id = res.json()["id"]
        
        # 6. Assign character to scene
        res = client.post(f"/scenes/{cls.scene_id}/characters/{cls.character_id}")
        assert res.status_code == 201, res.text

    def test_01_get_default_scene_direction(self):
        """Verify GET /scenes/{scene_id}/direction returns calculated default events."""
        res = client.get(f"/scenes/{self.scene_id}/direction")
        self.assertEqual(res.status_code, 200)
        
        data = res.json()
        self.assertEqual(data["scene_id"], self.scene_id)
        self.assertEqual(data["scene_title"], "Scene 17 Outer Space")
        self.assertEqual(data["narration"], "In the cold depth of space...")
        self.assertEqual(data["camera_notes"], "Follow space ship")
        self.assertEqual(data["duration_seconds"], 12.0)
        
        # Verify shots are present (storyboard generates at least 3 shots for 1 character)
        shots = data["shots"]
        self.assertGreaterEqual(len(shots), 3)
        
        # Verify first shot content
        first_shot = shots[0]
        self.assertEqual(first_shot["shot_number"], 1)
        self.assertEqual(first_shot["shot_type"], "Wide")
        self.assertEqual(first_shot["camera_angle"], "High Angle")
        
        # Verify default timeline events are populated
        timeline = first_shot["timeline"]
        categories = [e["category"] for e in timeline]
        self.assertIn("camera", categories)
        self.assertIn("character", categories)
        self.assertIn("environment", categories)
        self.assertIn("effects", categories)
        self.assertIn("audio", categories)
        
        # Verify keyframes
        keyframes = first_shot["estimated_keyframes"]
        self.assertEqual(len(keyframes), 3)
        self.assertEqual(keyframes[0]["timestamp"], 0.0)
        self.assertEqual(keyframes[2]["timestamp"], first_shot["duration_seconds"])

    def test_02_update_scene_direction(self):
        """Verify PUT /scenes/{scene_id}/direction saves custom timeline events."""
        custom_payload = {
            "timeline_events": [
                {
                    "shot_number": 1,
                    "timestamp": 1.2,
                    "category": "camera",
                    "action": "orbit",
                    "parameters": {"speed": "fast", "radius": 10.0}
                },
                {
                    "shot_number": 1,
                    "timestamp": 2.5,
                    "category": "character",
                    "action": "blink",
                    "parameters": {"character_name": "Captain-17"}
                }
            ]
        }
        res = client.put(f"/scenes/{self.scene_id}/direction", json=custom_payload)
        self.assertEqual(res.status_code, 200)
        
        data = res.json()
        first_shot = data["shots"][0]
        timeline = first_shot["timeline"]
        
        # We customized shot 1, so it should only have our 2 custom events
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[0]["action"], "orbit")
        self.assertEqual(timeline[0]["timestamp"], 1.2)
        self.assertEqual(timeline[1]["action"], "blink")
        self.assertEqual(timeline[1]["timestamp"], 2.5)
        
        # Other shots should still fallback to default events
        second_shot = data["shots"][1]
        self.assertGreater(len(second_shot["timeline"]), 0)

    def test_03_get_custom_scene_direction(self):
        """Verify GET returns the saved custom events from database."""
        res = client.get(f"/scenes/{self.scene_id}/direction")
        self.assertEqual(res.status_code, 200)
        
        data = res.json()
        first_shot = data["shots"][0]
        timeline = first_shot["timeline"]
        
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[0]["action"], "orbit")

    def test_04_invalid_scene_direction_returns_404(self):
        """Verify 404 behavior for invalid scene IDs."""
        res_get = client.get("/scenes/99999/direction")
        self.assertEqual(res_get.status_code, 404)
        
        res_put = client.put("/scenes/99999/direction", json={"timeline_events": []})
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
