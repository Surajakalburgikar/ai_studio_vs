"""
verify_sprint_25.py — Unit and Integration Tests for Sprint 25 Character Registry.
"""

import os
import sys
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup path so app is importable
sys.path.append(os.path.abspath("."))

# Configuration of test database
TEST_DB_FILE = "./test_temp25.db"
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
from app.models.story import Story
from app.models.character import Character
from app.services.ai.pipeline.pipeline_context import PipelineContext
from app.services.ai.models.character_profile import CharacterProfile
from app.services.ai.registry.character_normalizer import CharacterNormalizer
from app.services.ai.registry.character_matcher import CharacterMatcher
from app.services.ai.registry.character_profile_builder import CharacterProfileBuilder
from app.services.ai.registry.character_registry import CharacterRegistry
from app.services.ai.stages.story_stage import StoryStage
from app.services.ai.stages.scene_director_stage import SceneDirectorStage
from app.services.ai.stages.shot_planner_stage import ShotPlannerStage
from app.services.ai.stages.character_registry_stage import CharacterRegistryStage
from app.services.ai.pipeline.project_pipeline import ProjectPipeline
from app.services.ai.pipeline.production_summary import ProductionSummary


class TestCharacterNormalizer(unittest.TestCase):
    """Verify normalization and alias mapping resolution."""

    def test_name_casing_and_whitespace(self):
        norm = CharacterNormalizer()
        self.assertEqual(norm.normalize_basic("  kai  "), "Kai")
        self.assertEqual(norm.normalize_basic("KAI"), "Kai")
        self.assertEqual(norm.normalize_basic("kai o'connor"), "Kai O'Connor")

    def test_alias_resolution(self):
        norm = CharacterNormalizer(alias_mappings={"Commander Kai": "Kai"})
        self.assertEqual(norm.resolve_canonical("commander kai"), "Kai")
        self.assertEqual(norm.resolve_canonical("Kai"), "Kai")

    def test_detect_duplicates(self):
        norm = CharacterNormalizer(alias_mappings={"Commander Kai": "Kai"})
        names = ["kai", "KAI", "Commander Kai", "Zara"]
        unique = norm.detect_duplicates(names)
        self.assertEqual(unique, ["Kai", "Zara"])


class TestCharacterMatcher(unittest.TestCase):
    """Verify that candidate names are matched to database character records."""

    def setUp(self):
        self.db = TestSessionLocal()
        self.project = Project(
            title="Matcher Test Project",
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
        
        self.story = Story(title="Matcher Story", project_id=self.project.id)
        self.db.add(self.story)
        self.db.commit()
        self.db.refresh(self.story)

    def tearDown(self):
        self.db.close()

    def test_exact_and_alias_matching(self):
        char1 = Character(story_id=self.story.id, name="Kai", aliases="K, Commander Kai", role="hero", gender="male")
        self.db.add(char1)
        self.db.commit()
        
        normalizer = CharacterNormalizer()
        matcher = CharacterMatcher(normalizer)
        
        # 1. Exact Match
        match, score = matcher.find_best_match("kai", [char1])
        self.assertEqual(match.id, char1.id)
        self.assertEqual(score, 1.0)
        
        # 2. Alias Match
        match, score = matcher.find_best_match("commander kai", [char1])
        self.assertEqual(match.id, char1.id)
        self.assertEqual(score, 1.0)

        # 3. Substring/Fuzzy match
        match, score = matcher.find_best_match("Kai of the North", [char1])
        self.assertEqual(match.id, char1.id)
        self.assertTrue(0.0 < score < 1.0)


class TestCharacterRegistryPipeline(unittest.TestCase):
    """Verify E2E database creation, profile indexing, and stages execution."""

    def setUp(self):
        self.db = TestSessionLocal()
        self.project = Project(
            title="E2E Character Project",
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

    def test_character_registry_stage(self):
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
        
        # Inject candidate names to extract
        context.metadata["characters"] = ["Kai", "Commander Kai", "Zara"]

        # Run Story, SceneDirector, ShotPlanner
        StoryStage(self.db).run(context)
        SceneDirectorStage(self.db).run(context)
        ShotPlannerStage(self.db).run(context)

        # Run Stage
        stage = CharacterRegistryStage(self.db)
        updated_context = stage.run(context)

        # Verify PipelineContext fields are populated
        self.assertTrue(len(updated_context.characters) > 0)
        self.assertIn("Kai", updated_context.character_profiles)
        self.assertIn("Zara", updated_context.character_profiles)
        
        # Verify scene & shot indices
        self.assertIn("Kai", updated_context.character_scene_index)
        self.assertIn("Kai", updated_context.character_shot_index)

        # Assert new DB character records were persisted
        db_chars = self.db.query(Character).filter(Character.story_id == context.story.id).all()
        db_names = [c.name for c in db_chars]
        self.assertIn("Kai", db_names)
        self.assertIn("Zara", db_names)

    def test_project_pipeline_e2e(self):
        pipeline = ProjectPipeline(self.db)
        
        # Check stages ordering
        stage_names = [stage.__class__.__name__ for stage in pipeline.stages]
        self.assertEqual(
            stage_names, 
            ["StoryStage", "SceneDirectorStage", "ShotPlannerStage", "CharacterRegistryStage", "JobBuilderStage"]
        )

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
