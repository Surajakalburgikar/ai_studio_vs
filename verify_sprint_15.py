import os
import sys
import shutil
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 1. Setup paths
sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath("../AI_STUDIO_WORKER"))

# 2. Database config for testing
TEST_DB_FILE = "./test_temp15.db"
if os.path.exists(TEST_DB_FILE):
    os.remove(TEST_DB_FILE)

engine = create_engine(f"sqlite:///{TEST_DB_FILE}", connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import models & Base to register schemas
from app.database.base import Base
import app.models  # registers all models on Base

# Create tables in the test database
Base.metadata.create_all(bind=engine)

# Override FastAPI get_db dependency
from app.main import app
from app.database.session import get_db

def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# 3. Request interception to mock requests routing to TestClient
import requests
client = TestClient(app)

def mock_requests_to_testclient(test_client):
    original_get = requests.get
    original_post = requests.post
    original_patch = requests.patch

    def get(url, *args, **kwargs):
        if url.startswith("http://localhost:8000") or url.startswith("http://127.0.0.1:8000"):
            path = url.replace("http://localhost:8000", "").replace("http://127.0.0.1:8000", "")
            return test_client.get(path)
        return original_get(url, *args, **kwargs)

    def post(url, *args, **kwargs):
        if url.startswith("http://localhost:8000") or url.startswith("http://127.0.0.1:8000"):
            path = url.replace("http://localhost:8000", "").replace("http://127.0.0.1:8000", "")
            tc_kwargs = {}
            if "json" in kwargs:
                tc_kwargs["json"] = kwargs["json"]
            return test_client.post(path, **tc_kwargs)
        return original_post(url, *args, **kwargs)

    def patch(url, *args, **kwargs):
        if url.startswith("http://localhost:8000") or url.startswith("http://127.0.0.1:8000"):
            path = url.replace("http://localhost:8000", "").replace("http://127.0.0.1:8000", "")
            tc_kwargs = {}
            if "json" in kwargs:
                tc_kwargs["json"] = kwargs["json"]
            return test_client.patch(path, **tc_kwargs)
        return original_patch(url, *args, **kwargs)

    requests.get = get
    requests.post = post
    requests.patch = patch

# Apply request mocking
mock_requests_to_testclient(client)

# 4. Import worker classes AFTER adding to sys.path
from worker.jobs.fetch import JobFetcher
from worker.jobs.process import JobProcessor
from worker.reporter.reporter import Reporter
from worker.models.job import GenerationJob as WorkerJob

class Sprint15RegressionTests(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Setup test data via TestClient endpoints
        
        # Sprint 1: Project Management
        proj_payload = {
            "title": "Sprint 15 Project",
            "description": "Integration testing for Sprint 15",
            "video_type": "medium",
            "target_duration_seconds": 120,
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
        
        # Sprint 2/3: Stories
        story_payload = {
            "title": "Story 15",
            "genre": "Sci-Fi",
            "summary": "Testing sprint 15 integration",
            "story_text": "Once upon a time in Sprint 15..."
        }
        res = client.post(f"/projects/{cls.project_id}/stories", json=story_payload)
        assert res.status_code == 201, res.text
        cls.story_id = res.json()["id"]
        
        # Sprint 4: Episodes
        episode_payload = {
            "episode_number": 1,
            "title": "Episode 15",
            "summary": "Episode 15 summary"
        }
        res = client.post(f"/stories/{cls.story_id}/episodes", json=episode_payload)
        assert res.status_code == 201, res.text
        cls.episode_id = res.json()["id"]
        
        # Sprint 4: Scenes
        scene_payload = {
            "scene_number": 1,
            "title": "Scene 15",
            "narration": "Narration for Scene 15",
            "camera_notes": "Pan left",
            "duration_seconds": 15.0
        }
        res = client.post(f"/episodes/{cls.episode_id}/scenes", json=scene_payload)
        assert res.status_code == 201, res.text
        cls.scene_id = res.json()["id"]
        
        # Sprint 7: Character Registry
        char_payload = {
            "name": "Zee-15",
            "role": "Hero",
            "gender": "Non-binary",
            "description": "Android test character",
            "species": "Android",
            "body_type": "Metallic",
            "hair_style": "Bald",
            "eye_color": "Blue",
            "negative_prompt": "organic skin"
        }
        res = client.post(f"/stories/{cls.story_id}/characters", json=char_payload)
        assert res.status_code == 201, res.text
        cls.character_id = res.json()["id"]
        
        # Sprint 8: Scene Character Mapping
        res = client.post(f"/scenes/{cls.scene_id}/characters/{cls.character_id}")
        assert res.status_code == 201, res.text
        
        # Sprint 14: Job Creation
        job_create_payload = {
            "scene_id": cls.scene_id,
            "provider": "mock",
            "priority": 10
        }
        res = client.post("/jobs", json=job_create_payload)
        assert res.status_code == 201, res.text
        cls.jobs_created = res.json()
        assert len(cls.jobs_created) > 0, "No jobs created for scene storyboard"
    
    def test_01_backend_job_failed_endpoint(self):
        """Verify the new POST /jobs/{job_id}/failed endpoint works directly."""
        # Grab a created job ID
        target_job = self.jobs_created[0]
        job_id = target_job["id"]
        
        # Fail the job
        fail_payload = {"error_message": "Direct API failure injection test"}
        res = client.post(f"/jobs/{job_id}/failed", json=fail_payload)
        self.assertEqual(res.status_code, 200)
        
        data = res.json()
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["error_message"], "Direct API failure injection test")
        
        # Verify status matches in DB
        res_get = client.get(f"/jobs/next")
        # Since the first job was failed, next pending job should be fetched (if any), or 404
        # Let's clean up state by resetting status of first job to pending for further pipeline tests
        db = TestSessionLocal()
        from app.models.generation_job import GenerationJob
        job_db = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        job_db.status = "pending"
        job_db.error_message = None
        db.commit()
        db.close()

    def test_02_worker_pipeline_success(self):
        """Test successful execution pipeline: Started -> Execute -> Progress -> Completed."""
        fetcher = JobFetcher()
        job = fetcher.fetch_job()
        self.assertIsNotNone(job, "Failed to fetch next job")
        self.assertEqual(job.status, "processing")
        
        processor = JobProcessor()
        result = processor.process(job)
        
        self.assertTrue(result.success)
        self.assertEqual(result.provider, "mock")
        self.assertIn("scene_", result.image_path)
        
        # Retrieve the job state from database to check that it is completed
        db = TestSessionLocal()
        from app.models.generation_job import GenerationJob
        job_db = db.query(GenerationJob).filter(GenerationJob.id == job.id).first()
        self.assertEqual(job_db.status, "completed")
        self.assertEqual(job_db.progress, 100)
        self.assertEqual(job_db.drive_file_id, result.image_path)
        self.assertIsNotNone(job_db.generation_time)
        db.close()

    def test_03_worker_pipeline_failure(self):
        """Test pipeline exception handling: Started -> Execute (raises Exception) -> Failed."""
        # 1. Reset/Create another job and get it
        # Let's create a new job to keep tests independent
        job_create_payload = {
            "scene_id": self.scene_id,
            "provider": "mock",
            "priority": 100
        }
        res = client.post("/jobs", json=job_create_payload)
        self.assertEqual(res.status_code, 201)
        new_job_id = res.json()[0]["id"]
        
        fetcher = JobFetcher()
        job = fetcher.fetch_job()
        self.assertIsNotNone(job)
        self.assertEqual(job.id, new_job_id)
        
        # 2. Mock storage provider to fail
        processor = JobProcessor()
        original_save_image = processor.executor.storage_provider.save_image
        
        def mock_save_image(filename, image):
            raise RuntimeError("Disk is full! Failed to save image.")
        
        processor.executor.storage_provider.save_image = mock_save_image
        
        # 3. Process job and assert processor returns failed result
        result = processor.process(job)
        self.assertFalse(result.success)
        self.assertIn("Disk is full", result.message)
        
        # 4. Verify job state in database is marked as failed and error message saved
        db = TestSessionLocal()
        from app.models.generation_job import GenerationJob
        job_db = db.query(GenerationJob).filter(GenerationJob.id == job.id).first()
        self.assertEqual(job_db.status, "failed")
        self.assertIn("Disk is full", job_db.error_message)
        db.close()
        
        # Restore save_image
        processor.executor.storage_provider.save_image = original_save_image

    @classmethod
    def tearDownClass(cls):
        # Close engine and delete test db file
        engine.dispose()
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass
        
        # Clean up generated test output folders if any
        if os.path.exists("./generated"):
            pass # Keep or clean

if __name__ == "__main__":
    unittest.main()
