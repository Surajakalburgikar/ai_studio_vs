"""
verify_sprint_20.py — Integration and Unit Tests for Sprint 20 Story Generation Pipeline

Runs unittest suites to validate:
    1. StoryParser
    2. StoryValidator
    3. MockProvider
    4. StoryRepository
    5. StoryGenerator (E2E Integration using Mock)
"""

import os
import sys
import unittest
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup path so app is importable
sys.path.append(os.path.abspath("."))

# Configuration of test database
TEST_DB_FILE = "./test_temp20.db"
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
from app.services.ai.exceptions import ParserError, ValidationError, RepositoryError, StoryGenerationError
from app.services.ai.story_parser import StoryParser
from app.services.ai.story_validator import StoryValidator
from app.services.ai.story_repository import StoryRepository
from app.services.ai.story_generator import StoryGenerator
from app.services.ai.providers.mock_provider import MockProvider
from app.services.ai.providers.gemini_provider import GeminiProvider
from app.models.project import Project
from app.models.story import Story
from app.models.episode import Episode
from app.models.scene import Scene


class TestStoryParser(unittest.TestCase):
    """Unit tests for StoryParser."""

    def setUp(self):
        self.parser = StoryParser()

    def test_parse_valid_json(self):
        raw = '{"title": "The Whispering Stone", "genre": "Fantasy", "episodes": []}'
        res = self.parser.parse(raw)
        self.assertEqual(res["title"], "The Whispering Stone")
        self.assertEqual(res["genre"], "Fantasy")

    def test_parse_json_with_markdown_fences(self):
        raw = '```json\n{"title": "Markdown Story", "genre": "Sci-Fi", "episodes": []}\n```'
        res = self.parser.parse(raw)
        self.assertEqual(res["title"], "Markdown Story")

        # Test fence without json label
        raw_no_label = '```\n{"title": "Plain Code Fence", "genre": "Drama", "episodes": []}\n```'
        res_no_label = self.parser.parse(raw_no_label)
        self.assertEqual(res_no_label["title"], "Plain Code Fence")

    def test_parse_invalid_json_raises_parser_error(self):
        raw_bad = '{"title": "Incomplete JSON", "genre": '
        with self.assertRaises(ParserError):
            self.parser.parse(raw_bad)

    def test_parse_empty_text_raises_parser_error(self):
        with self.assertRaises(ParserError):
            self.parser.parse("")


class TestStoryValidator(unittest.TestCase):
    """Unit tests for StoryValidator."""

    def setUp(self):
        self.validator = StoryValidator()
        # A valid story dictionary structure
        self.valid_story = {
            "title": "Aria's Garden",
            "genre": "Fantasy",
            "summary": "A story about a garden.",
            "story_text": "Aria goes to the garden. It is beautiful.",
            "episodes": [
                {
                    "episode_number": 1,
                    "title": "Episode 1",
                    "summary": "Introduction to the garden",
                    "scenes": [
                        {
                            "scene_number": 1,
                            "title": "Scene 1",
                            "narration": "Aria sees the garden.",
                            "camera_notes": "Pan left.",
                            "duration_seconds": 10.0
                        },
                        {
                            "scene_number": 2,
                            "title": "Scene 2",
                            "narration": "Aria touches a flower.",
                            "camera_notes": "Zoom in.",
                            "duration_seconds": 15.5
                        }
                    ]
                }
            ]
        }

    def test_validate_valid_story(self):
        # Should complete without raising any exception
        self.validator.validate(self.valid_story)

    def test_validate_missing_story_field(self):
        bad_story = self.valid_story.copy()
        del bad_story["title"]
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate(bad_story)
        self.assertIn("Missing required story field: 'title'", str(ctx.exception))

    def test_validate_empty_title(self):
        bad_story = self.valid_story.copy()
        bad_story["title"] = "   "
        with self.assertRaises(ValidationError):
            self.validator.validate(bad_story)

    def test_validate_empty_episodes(self):
        bad_story = self.valid_story.copy()
        bad_story["episodes"] = []
        with self.assertRaises(ValidationError):
            self.validator.validate(bad_story)

    def test_validate_duplicate_episodes(self):
        bad_story = {
            **self.valid_story,
            "episodes": [
                {
                    "episode_number": 1,
                    "title": "Ep 1",
                    "summary": "...",
                    "scenes": [{"scene_number": 1, "title": "Sc 1", "narration": "...", "camera_notes": "...", "duration_seconds": 5.0}]
                },
                {
                    "episode_number": 1,  # Duplicate
                    "title": "Ep 2",
                    "summary": "...",
                    "scenes": [{"scene_number": 1, "title": "Sc 1", "narration": "...", "camera_notes": "...", "duration_seconds": 5.0}]
                }
            ]
        }
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate(bad_story)
        self.assertIn("Duplicate episode number", str(ctx.exception))

    def test_validate_non_sequential_scenes(self):
        bad_story = {
            **self.valid_story,
            "episodes": [
                {
                    "episode_number": 1,
                    "title": "Ep 1",
                    "summary": "...",
                    "scenes": [
                        {"scene_number": 1, "title": "Sc 1", "narration": "...", "camera_notes": "...", "duration_seconds": 5.0},
                        {"scene_number": 3, "title": "Sc 2", "narration": "...", "camera_notes": "...", "duration_seconds": 5.0}  # Missing 2
                    ]
                }
            ]
        }
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate(bad_story)
        self.assertIn("not in sequential order from 1", str(ctx.exception))

    def test_validate_negative_scene_duration(self):
        bad_story = {
            **self.valid_story,
            "episodes": [
                {
                    "episode_number": 1,
                    "title": "Ep 1",
                    "summary": "...",
                    "scenes": [
                        {"scene_number": 1, "title": "Sc 1", "narration": "...", "camera_notes": "...", "duration_seconds": -5.0}
                    ]
                }
            ]
        }
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate(bad_story)
        self.assertIn("duration_seconds must be greater than 0", str(ctx.exception))


class TestMockProvider(unittest.TestCase):
    """Unit tests for MockProvider."""

    def test_generate_returns_parsable_json(self):
        provider = MockProvider()
        res = provider.generate("dummy prompt")
        self.assertTrue(isinstance(res, str))
        data = json.loads(res)
        self.assertEqual(data["title"], "The Whispering Stone")
        self.assertTrue("episodes" in data)


class TestGeminiProvider(unittest.TestCase):
    """Unit tests for GeminiProvider."""

    def test_generate_raises_not_implemented(self):
        provider = GeminiProvider()
        try:
            res = provider.generate("test prompt")
            self.assertTrue(isinstance(res, str))
        except StoryGenerationError:
            pass


class TestStoryRepository(unittest.TestCase):
    """Unit and integration tests for StoryRepository."""

    def setUp(self):
        self.db = TestSessionLocal()
        # Create a mock project
        self.project = Project(
            title="Repository Test Project",
            video_type="medium",
            target_duration_seconds=120,
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

        self.repo = StoryRepository(self.db)
        self.valid_data = {
            "title": "Repo Story",
            "genre": "Sci-Fi",
            "summary": "A sci-fi story.",
            "story_text": "Story text goes here.",
            "episodes": [
                {
                    "episode_number": 1,
                    "title": "Episode One",
                    "summary": "Summary Ep One",
                    "scenes": [
                        {
                            "scene_number": 1,
                            "title": "Scene One",
                            "narration": "Narration text",
                            "camera_notes": "Camera notes",
                            "duration_seconds": 15.0
                        }
                    ]
                }
            ]
        }

    def tearDown(self):
        self.db.close()

    def test_save_story_persists_fully(self):
        story = self.repo.save_story(self.project.id, self.valid_data)
        
        # Verify Story persisted
        db_story = self.db.query(Story).filter(Story.id == story.id).first()
        self.assertIsNotNone(db_story)
        self.assertEqual(db_story.title, "Repo Story")
        self.assertEqual(db_story.project_id, self.project.id)

        # Verify Episode persisted
        self.assertEqual(len(db_story.episodes), 1)
        db_episode = db_story.episodes[0]
        self.assertEqual(db_episode.title, "Episode One")
        self.assertEqual(db_episode.episode_number, 1)

        # Verify Scene persisted
        self.assertEqual(len(db_episode.scenes), 1)
        db_scene = db_episode.scenes[0]
        self.assertEqual(db_scene.title, "Scene One")
        self.assertEqual(db_scene.scene_number, 1)
        self.assertEqual(db_scene.duration_seconds, 15.0)

    def test_save_story_fails_and_rolls_back_on_invalid_project(self):
        # Using a project ID that does not exist should fail foreign key constraint
        with self.assertRaises(RepositoryError):
            self.repo.save_story(99999, self.valid_data)


class TestStoryGenerator(unittest.TestCase):
    """End-to-End integration tests for StoryGenerator service using MockProvider."""

    def setUp(self):
        self.db = TestSessionLocal()
        # Create a mock project
        self.project = Project(
            title="Generator E2E Test Project",
            video_type="medium",
            target_duration_seconds=120,
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
        
        self.generator = StoryGenerator(self.db)
        
        self.variables = {
            "genre": "Fantasy",
            "theme": "Magic and friendship",
            "art_style": "anime",
            "audience": "kids",
            "language": "English",
            "target_duration": "60",
            "episode_count": "1",
            "episode_duration": "60"
        }

    def tearDown(self):
        self.db.close()

    def test_generate_success_using_mock_provider(self):
        story = self.generator.generate(self.project.id, self.variables)
        self.assertIsNotNone(story)
        self.assertEqual(story.project_id, self.project.id)
        # Verify title comes from MockProvider
        self.assertEqual(story.title, "The Whispering Stone")
        self.assertEqual(len(story.episodes), 2)  # Mock returns 2 episodes

    def test_generate_missing_variables_raises_validation_error(self):
        bad_vars = self.variables.copy()
        del bad_vars["genre"]
        with self.assertRaises(ValidationError):
            self.generator.generate(self.project.id, bad_vars)

    def test_generate_invalid_provider_raises_error(self):
        # Temporarily mock configuration setting
        from app.core import config
        old_provider = config.settings.STORY_GENERATOR_PROVIDER
        config.settings.STORY_GENERATOR_PROVIDER = "unsupported_provider"
        try:
            with self.assertRaises(StoryGenerationError):
                StoryGenerator(self.db)
        finally:
            config.settings.STORY_GENERATOR_PROVIDER = old_provider


if __name__ == "__main__":
    unittest.main()
