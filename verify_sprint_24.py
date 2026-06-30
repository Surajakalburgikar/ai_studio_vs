"""
verify_sprint_24.py — Unit and Integration Tests for Sprint 24 Shot Planner.
"""

import os
import sys
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup path so app is importable
sys.path.append(os.path.abspath("."))

# Configuration of test database
TEST_DB_FILE = "./test_temp24.db"
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
from app.services.ai.models.shot_plan import ShotPlan
from app.services.ai.planners.shot_planner import ShotPlanner
from app.services.ai.stages.story_stage import StoryStage
from app.services.ai.stages.scene_director_stage import SceneDirectorStage
from app.services.ai.stages.shot_planner_stage import ShotPlannerStage
from app.services.ai.pipeline.project_pipeline import ProjectPipeline
from app.services.ai.pipeline.production_summary import ProductionSummary


class TestShotPlanModel(unittest.TestCase):
    """Verify that ShotPlan dataclass fields are correct."""

    def test_shot_plan_instantiation(self):
        plan = ShotPlan(
            scene_id=10,
            shot_number=1,
            shot_type="Wide Shot",
            camera_angle="Eye Level",
            camera_movement="Static",
            composition="Rule of Thirds",
            focus_subject="Landscape",
            duration_seconds=4.5,
            transition_in="Fade In",
            transition_out="Cut",
            description="Landscape wide view.",
            visual_notes="Moody lighting.",
            scene_direction_id=20,
            metadata={"priority": "high"}
        )
        self.assertEqual(plan.scene_id, 10)
        self.assertEqual(plan.shot_number, 1)
        self.assertEqual(plan.shot_type, "Wide Shot")
        self.assertEqual(plan.camera_angle, "Eye Level")
        self.assertEqual(plan.camera_movement, "Static")
        self.assertEqual(plan.composition, "Rule of Thirds")
        self.assertEqual(plan.focus_subject, "Landscape")
        self.assertEqual(plan.duration_seconds, 4.5)
        self.assertEqual(plan.transition_in, "Fade In")
        self.assertEqual(plan.transition_out, "Cut")
        self.assertEqual(plan.description, "Landscape wide view.")
        self.assertEqual(plan.visual_notes, "Moody lighting.")
        self.assertEqual(plan.scene_direction_id, 20)
        self.assertEqual(plan.metadata["priority"], "high")


class TestShotPlannerRules(unittest.TestCase):
    """Verify planning rules under short, medium, and long durations."""

    def test_planning_rules_short_scene(self):
        sd = SceneDirection(
            scene_id=1,
            mood="Dramatic",
            lighting="Dramatic lighting",
            primary_focus="A character standing",
            camera_style="Fixed",
            composition_rule="Rule of Thirds",
            camera_movement="Static",
            visual_notes="None",
            suggested_shots=[
                ShotDirection(1, "Medium Shot", "Eye Level", "Static", "Rule of Thirds", 4.0, "Actor", "Narration text")
            ],
            estimated_duration=8.0  # Short: <= 10.0s
        )
        planner = ShotPlanner()
        plans = planner.plan_shots([sd])
        
        # Short scenes: 1-2 shots
        self.assertTrue(1 <= len(plans) <= 2)
        
        # Rule: Wide shot first
        self.assertEqual(plans[0].shot_type, "Establishing")
        
        # Rule: Transitions
        self.assertEqual(plans[0].transition_in, "Fade In")
        self.assertEqual(plans[-1].transition_out, "Fade Out")

    def test_planning_rules_long_scene(self):
        sd = SceneDirection(
            scene_id=2,
            mood="Dramatic",  # Emotional
            lighting="Dramatic lighting",
            primary_focus="Characters fighting",
            camera_style="Action handheld",
            composition_rule="Rule of Thirds",
            camera_movement="Tracking",
            visual_notes="None",
            suggested_shots=[
                ShotDirection(1, "Wide Shot", "Eye Level", "Static", "Rule of Thirds", 5.0, "Landscape", "Description"),
                ShotDirection(2, "Medium Shot", "Eye Level", "Pan", "Leading Lines", 5.0, "Actor", "Description"),
            ],
            estimated_duration=30.0  # Long: > 20.0s
        )
        planner = ShotPlanner()
        plans = planner.plan_shots([sd])
        
        # Long scenes: 5-8 shots
        self.assertTrue(5 <= len(plans) <= 8)
        
        # Rule: Close-up near emotional moments (mood is Dramatic)
        shot_types = [p.shot_type for p in plans]
        self.assertIn("Close-up", shot_types)

        # Rule: Respect estimated duration
        total_duration = sum(p.duration_seconds for p in plans)
        self.assertAlmostEqual(total_duration, 30.0, places=1)


class TestPipelineE2E(unittest.TestCase):
    """Verify ShotPlannerStage and ProjectPipeline execute successfully."""

    def setUp(self):
        self.db = TestSessionLocal()
        self.project = Project(
            title="E2E Shot Planner Project",
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

    def test_shot_planner_stage_execution(self):
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
        
        # Run StoryStage and SceneDirectorStage
        StoryStage(self.db).run(context)
        SceneDirectorStage(self.db).run(context)
        
        # Run ShotPlannerStage
        stage = ShotPlannerStage(self.db)
        updated_context = stage.run(context)
        
        self.assertTrue(len(updated_context.shot_plans) > 0)
        self.assertIn("ShotPlannerStage_started", updated_context.timestamps)
        self.assertIn("ShotPlannerStage_completed", updated_context.timestamps)

    def test_project_pipeline_e2e(self):
        pipeline = ProjectPipeline(self.db)
        
        # Check stages ordering
        stage_names = [stage.__class__.__name__ for stage in pipeline.stages]
        self.assertEqual(stage_names, ["StoryStage", "SceneDirectorStage", "ShotPlannerStage", "JobBuilderStage"])

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
