"""
verify_sprint_22.py — Sprint 22 Orchestrator Verification Suite

Runs unittest suites to validate:
    1. PipelineContext structure and fields.
    2. StoryStage execution.
    3. JobBuilder and job creation.
    4. ProductionSummary mapping.
    5. E2E ProjectPipeline execution, verifying the creation of Story,
       Episode, Scene, and GenerationJobs.
"""

import os
import sys
import unittest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup path so app is importable
sys.path.append(os.path.abspath("."))

# Configuration of test database
TEST_DB_FILE = "./test_temp22.db"
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
from app.models.project import Project
from app.services.ai.pipeline_context import PipelineContext
from app.services.ai.stages.story_stage import StoryStage
from app.services.ai.stages.job_builder_stage import JobBuilderStage
from app.services.ai.job_builder import JobBuilder
from app.services.ai.project_pipeline import ProjectPipeline
from app.services.ai.production_summary import ProductionSummary


class TestPipelineContext(unittest.TestCase):
    """Verify that PipelineContext contains all required fields and behaves as expected."""

    def test_context_fields(self):
        project = Project(title="Context Test")
        context = PipelineContext(project=project)
        
        self.assertEqual(context.project, project)
        self.assertIsNone(context.story)
        self.assertEqual(context.episodes, [])
        self.assertEqual(context.scenes, [])
        self.assertEqual(context.generation_jobs, [])
        self.assertEqual(context.metadata, {})
        self.assertEqual(context.warnings, [])
        self.assertEqual(context.errors, [])
        self.assertEqual(context.status, "pending")
        self.assertEqual(context.timestamps, {})


class TestOrchestratorComponents(unittest.TestCase):
    """Test individual orchestrator components: StoryStage, JobBuilder, ProductionSummary."""

    def setUp(self):
        self.db = TestSessionLocal()
        self.project = Project(
            title="Orchestration Component Project",
            video_type="medium",
            target_duration_seconds=60,
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

    def tearDown(self):
        self.db.close()

    def test_story_stage_execution(self):
        context = PipelineContext(project=self.project)
        # Using mock variables to speed up execution and run offline
        context.metadata["variables"] = {
            "genre": "Fantasy",
            "theme": "Magic stones",
            "art_style": "anime",
            "audience": "kids",
            "language": "English",
            "target_duration": "60",
            "episode_count": "1",
            "episode_duration": "60"
        }
        
        stage = StoryStage(self.db)
        updated_context = stage.run(context)
        
        self.assertIsNotNone(updated_context.story)
        self.assertEqual(updated_context.story.project_id, self.project.id)
        self.assertTrue(len(updated_context.episodes) > 0)
        self.assertTrue(len(updated_context.scenes) > 0)
        self.assertIn("StoryStage_started", updated_context.timestamps)
        self.assertIn("StoryStage_completed", updated_context.timestamps)

    def test_job_builder_creation(self):
        # 1. Run StoryStage first to get scenes
        context = PipelineContext(project=self.project)
        context.metadata["variables"] = {
            "genre": "Fantasy",
            "theme": "Magic stones",
            "art_style": "anime",
            "audience": "kids",
            "language": "English",
            "target_duration": "60",
            "episode_count": "1",
            "episode_duration": "60"
        }
        StoryStage(self.db).run(context)
        
        # 2. Run JobBuilder
        builder = JobBuilder(self.db)
        jobs = builder.build_jobs(context.scenes)
        
        self.assertTrue(len(jobs) > 0)
        for job in jobs:
            self.assertEqual(job.status, "pending")
            self.assertIsNotNone(job.scene_id)
            self.assertTrue(job.shot_number > 0)
            self.assertIsNotNone(job.prompt)


class TestProjectPipelineE2E(unittest.TestCase):
    """End-to-End tests for ProjectPipeline running all stages sequentially."""

    def setUp(self):
        self.db = TestSessionLocal()
        self.project = Project(
            title="E2E Pipeline Project",
            video_type="medium",
            target_duration_seconds=60,
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

    def tearDown(self):
        self.db.close()

    def test_pipeline_execution_success(self):
        pipeline = ProjectPipeline(self.db)
        variables = {
            "genre": "Sci-Fi",
            "theme": "Cyberpunk city",
            "art_style": "anime",
            "audience": "adults",
            "language": "English",
            "target_duration": "60",
            "episode_count": "1",
            "episode_duration": "60"
        }

        # Run pipeline
        summary = pipeline.generate_project(self.project.id, variables)

        # Assert ProductionSummary outputs
        self.assertIsInstance(summary, ProductionSummary)
        self.assertEqual(summary.project_id, self.project.id)
        self.assertIsNotNone(summary.story_id)
        self.assertTrue(summary.episode_count > 0)
        self.assertTrue(summary.scene_count > 0)
        self.assertTrue(summary.job_count > 0)
        self.assertTrue(summary.estimated_duration > 0)
        self.assertTrue(summary.pipeline_duration > 0)
        self.assertEqual(summary.status, "completed")

        # Double check database persistence of Story, Episodes, Scenes, and Jobs
        from app.models.story import Story
        from app.models.episode import Episode
        from app.models.scene import Scene
        from app.models.generation_job import GenerationJob

        db_story = self.db.query(Story).filter(Story.project_id == self.project.id).first()
        self.assertIsNotNone(db_story)
        self.assertEqual(db_story.id, summary.story_id)

        db_episodes = self.db.query(Episode).filter(Episode.story_id == db_story.id).all()
        self.assertEqual(len(db_episodes), summary.episode_count)

        db_scenes = self.db.query(Scene).join(Episode).filter(Episode.story_id == db_story.id).all()
        self.assertEqual(len(db_scenes), summary.scene_count)

        db_jobs = self.db.query(GenerationJob).filter(GenerationJob.scene_id == db_scenes[0].id).all()
        self.assertTrue(len(db_jobs) > 0)


if __name__ == "__main__":
    unittest.main()
