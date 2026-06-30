"""
verify_sprint_23.py — Integration and Unit Tests for Sprint 23 Scene Director

Runs unittest suites to validate:
    1. Framing and composition enums (ShotType, CameraMovement, CompositionRule).
    2. SceneDirector logic and context population.
    3. Metadata serialization formats.
    4. ProjectPipeline E2E integration with SceneDirectorStage.
"""

import os
import sys
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup path so app is importable
sys.path.append(os.path.abspath("."))

# Configuration of test database
TEST_DB_FILE = "./test_temp23.db"
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
from app.services.ai.directors.shot_types import ShotType
from app.services.ai.directors.camera_language import CameraMovement
from app.services.ai.directors.composition_rules import CompositionRule
from app.services.ai.directors.scene_director import SceneDirector
from app.services.ai.stages.story_stage import StoryStage
from app.services.ai.stages.scene_director_stage import SceneDirectorStage
from app.services.ai.project_pipeline import ProjectPipeline
from app.services.ai.production_summary import ProductionSummary


class TestCinematicEnums(unittest.TestCase):
    """Verify enums contain all required configuration styles."""

    def test_shot_types(self):
        self.assertEqual(ShotType.WIDE.value, "Wide Shot")
        self.assertEqual(ShotType.MEDIUM.value, "Medium Shot")
        self.assertEqual(ShotType.CLOSE_UP.value, "Close-up")
        self.assertEqual(ShotType.EXTREME_CLOSE_UP.value, "Extreme Close-up")
        self.assertEqual(ShotType.OVER_SHOULDER.value, "Over Shoulder")
        self.assertEqual(ShotType.POV.value, "POV")
        self.assertEqual(ShotType.TRACKING.value, "Tracking")
        self.assertEqual(ShotType.ESTABLISHING.value, "Establishing")

    def test_camera_movement(self):
        self.assertEqual(CameraMovement.PAN.value, "Pan")
        self.assertEqual(CameraMovement.TILT.value, "Tilt")
        self.assertEqual(CameraMovement.ZOOM.value, "Zoom")
        self.assertEqual(CameraMovement.DOLLY.value, "Dolly")
        self.assertEqual(CameraMovement.STATIC.value, "Static")
        self.assertEqual(CameraMovement.ORBIT.value, "Orbit")

    def test_composition_rules(self):
        self.assertEqual(CompositionRule.RULE_OF_THIRDS.value, "Rule of Thirds")
        self.assertEqual(CompositionRule.LEADING_LINES.value, "Leading Lines")
        self.assertEqual(CompositionRule.CENTER_COMPOSITION.value, "Center Composition")
        self.assertEqual(CompositionRule.NEGATIVE_SPACE.value, "Negative Space")
        self.assertEqual(CompositionRule.FOREGROUND_FRAMING.value, "Foreground Framing")


class TestSceneDirector(unittest.TestCase):
    """Unit tests for SceneDirector planning logic."""

    def setUp(self):
        self.db = TestSessionLocal()
        self.project = Project(
            title="Director Test Project",
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

    def test_direct_scenes_metadata_generation(self):
        # 1. Prepare pipeline context using StoryStage
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
        
        StoryStage(self.db).run(context)
        self.assertTrue(len(context.scenes) > 0)
        
        # 2. Run SceneDirector
        director = SceneDirector(self.db)
        updated_context = director.direct_scenes(context)
        
        # 3. Assert scene_direction metadata presence and structure
        self.assertIn("scene_direction", updated_context.metadata)
        directions = updated_context.metadata["scene_direction"]
        self.assertIn("scenes", directions)
        self.assertEqual(len(directions["scenes"]), len(context.scenes))
        
        # Validate format of first scene direction
        first_scene = directions["scenes"][0]
        self.assertEqual(first_scene["scene_id"], context.scenes[0].id)
        self.assertIn("direction", first_scene)
        
        direction_details = first_scene["direction"]
        self.assertIn("mood", direction_details)
        self.assertIn("lighting", direction_details)
        self.assertIn("primary_focus", direction_details)
        self.assertIn("camera_style", direction_details)
        self.assertIn("suggested_shot_sequence", direction_details)
        self.assertIn("visual_notes", direction_details)
        
        # Check enums mapping within suggested shot sequence
        shots = direction_details["suggested_shot_sequence"]
        self.assertTrue(len(shots) > 0)
        self.assertEqual(shots[0]["shot_type"], ShotType.ESTABLISHING.value)
        self.assertEqual(shots[0]["movement"], CameraMovement.STATIC.value)
        self.assertEqual(shots[0]["composition"], CompositionRule.RULE_OF_THIRDS.value)


class TestProjectPipelineIntegration(unittest.TestCase):
    """End-to-End integration tests for ProjectPipeline with SceneDirectorStage."""

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

    def test_pipeline_execution_success_with_director(self):
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

        # Assert Stage Types ordering
        stage_names = [stage.__class__.__name__ for stage in pipeline.stages]
        self.assertEqual(stage_names, ["StoryStage", "SceneDirectorStage", "ShotPlannerStage", "CharacterRegistryStage", "JobBuilderStage"])

        # Execute E2E pipeline
        summary = pipeline.generate_project(self.project.id, variables)

        self.assertIsInstance(summary, ProductionSummary)
        self.assertEqual(summary.status, "completed")
        self.assertTrue(summary.job_count > 0)


if __name__ == "__main__":
    unittest.main()
