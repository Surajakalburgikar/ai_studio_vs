"""
verify_sprint_23_5.py — Unit and Integration Tests for Sprint 23.5 Scene Direction Refactor.
"""

import os
import sys
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup path so app is importable
sys.path.append(os.path.abspath("."))

# Configuration of test database
TEST_DB_FILE = "./test_temp23_5.db"
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
from app.services.ai.pipeline.pipeline_context import PipelineContext
from app.services.ai.models.scene_direction import SceneDirection
from app.services.ai.models.shot_direction import ShotDirection
from app.services.ai.directors.scene_director import SceneDirector
from app.services.ai.stages.story_stage import StoryStage
from app.services.ai.stages.scene_director_stage import SceneDirectorStage
from app.services.ai.pipeline.project_pipeline import ProjectPipeline
from app.services.ai.pipeline.production_summary import ProductionSummary


class TestSceneDirectionModels(unittest.TestCase):
    """Verify that SceneDirection and ShotDirection dataclasses have all requested fields and types."""

    def test_shot_direction_instantiation(self):
        shot = ShotDirection(
            shot_number=1,
            shot_type="Extreme Close-up",
            camera_angle="Low Angle",
            camera_movement="Pan",
            composition="Rule of Thirds",
            duration_seconds=3.5,
            focus_subject="Protagonist's eyes",
            description="Close-up on protagonist looking shocked.",
            notes="Use high depth of field."
        )
        self.assertEqual(shot.shot_number, 1)
        self.assertEqual(shot.shot_type, "Extreme Close-up")
        self.assertEqual(shot.camera_angle, "Low Angle")
        self.assertEqual(shot.camera_movement, "Pan")
        self.assertEqual(shot.composition, "Rule of Thirds")
        self.assertEqual(shot.duration_seconds, 3.5)
        self.assertEqual(shot.focus_subject, "Protagonist's eyes")
        self.assertEqual(shot.description, "Close-up on protagonist looking shocked.")
        self.assertEqual(shot.notes, "Use high depth of field.")

    def test_scene_direction_instantiation(self):
        shot = ShotDirection(
            shot_number=1,
            shot_type="Wide Shot",
            camera_angle="Eye Level",
            camera_movement="Static",
            composition="Rule of Thirds",
            duration_seconds=5.0,
            focus_subject="Castle gates",
            description="Distant shot of castle gates opening."
        )
        direction = SceneDirection(
            scene_id=42,
            mood="Dramatic",
            lighting="Chiaroscuro",
            primary_focus="Castle opening",
            camera_style="Fixed wide",
            composition_rule="Rule of Thirds",
            camera_movement="Static",
            visual_notes="Ensure strong contrast.",
            suggested_shots=[shot],
            estimated_duration=5.0,
            metadata={"source": "AI Generator"}
        )
        self.assertEqual(direction.scene_id, 42)
        self.assertEqual(direction.mood, "Dramatic")
        self.assertEqual(direction.lighting, "Chiaroscuro")
        self.assertEqual(direction.primary_focus, "Castle opening")
        self.assertEqual(direction.camera_style, "Fixed wide")
        self.assertEqual(direction.composition_rule, "Rule of Thirds")
        self.assertEqual(direction.camera_movement, "Static")
        self.assertEqual(direction.visual_notes, "Ensure strong contrast.")
        self.assertEqual(len(direction.suggested_shots), 1)
        self.assertEqual(direction.suggested_shots[0].shot_number, 1)
        self.assertEqual(direction.estimated_duration, 5.0)
        self.assertEqual(direction.metadata["source"], "AI Generator")


class TestPipelineContextUpdate(unittest.TestCase):
    """Verify that PipelineContext includes scene_directions and can be updated by the SceneDirector."""

    def setUp(self):
        self.db = TestSessionLocal()
        self.project = Project(
            title="Refactor Test Project",
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
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass

    def test_pipeline_context_has_scene_directions(self):
        context = PipelineContext(project=self.project)
        self.assertTrue(hasattr(context, "scene_directions"))
        self.assertIsInstance(context.scene_directions, list)
        self.assertEqual(len(context.scene_directions), 0)

    def test_scene_director_populates_models_and_metadata(self):
        context = PipelineContext(project=self.project)
        context.metadata["variables"] = {
            "genre": "Fantasy",
            "theme": "Runic stone",
            "art_style": "anime",
            "audience": "kids",
            "language": "English",
            "target_duration": "60",
            "episode_count": "1",
            "episode_duration": "60"
        }
        
        # 1. Run StoryStage to generate scenes
        StoryStage(self.db).run(context)
        self.assertTrue(len(context.scenes) > 0)
        
        # 2. Run SceneDirector
        director = SceneDirector(self.db)
        updated_context = director.direct_scenes(context)
        
        # 3. Assert typed scene_directions list is populated
        self.assertEqual(len(updated_context.scene_directions), len(context.scenes))
        for scene_dir in updated_context.scene_directions:
            self.assertIsInstance(scene_dir, SceneDirection)
            self.assertTrue(scene_dir.scene_id > 0)
            self.assertTrue(len(scene_dir.suggested_shots) > 0)
            for shot in scene_dir.suggested_shots:
                self.assertIsInstance(shot, ShotDirection)
                self.assertTrue(shot.shot_number > 0)

        # 4. Assert backward-compatibility metadata is also populated
        self.assertIn("scene_direction", updated_context.metadata)
        self.assertEqual(len(updated_context.metadata["scene_direction"]["scenes"]), len(context.scenes))


class TestStageAndPipelineE2E(unittest.TestCase):
    """Verify that Stage wraps SceneDirector and ProjectPipeline executes successfully."""

    def setUp(self):
        self.db = TestSessionLocal()
        self.project = Project(
            title="E2E Refactor Project",
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
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass

    def test_scene_director_stage_execution(self):
        context = PipelineContext(project=self.project)
        context.metadata["variables"] = {
            "genre": "Sci-Fi",
            "theme": "Cyberpunk city",
            "art_style": "anime",
            "audience": "kids",
            "language": "English",
            "target_duration": "60",
            "episode_count": "1",
            "episode_duration": "60"
        }
        
        StoryStage(self.db).run(context)
        
        # Run Stage
        stage = SceneDirectorStage(self.db)
        updated_context = stage.run(context)
        
        self.assertEqual(len(updated_context.scene_directions), len(context.scenes))
        self.assertIn("SceneDirectorStage_started", updated_context.timestamps)
        self.assertIn("SceneDirectorStage_completed", updated_context.timestamps)

    def test_project_pipeline_execution_e2e(self):
        pipeline = ProjectPipeline(self.db)
        variables = {
            "genre": "Fantasy",
            "theme": "Runic stone",
            "art_style": "anime",
            "audience": "kids",
            "language": "English",
            "target_duration": "60",
            "episode_count": "1",
            "episode_duration": "60"
        }
        
        summary = pipeline.generate_project(self.project.id, variables)
        self.assertIsInstance(summary, ProductionSummary)
        self.assertEqual(summary.status, "completed")
        self.assertTrue(summary.job_count > 0)


if __name__ == "__main__":
    unittest.main()
