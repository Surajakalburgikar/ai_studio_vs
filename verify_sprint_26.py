"""
verify_sprint_26.py — Unit and integration tests for Sprint 26 Prompt Builder.
"""

import os
import sys
import unittest

# Setup path so app is importable
sys.path.append(os.path.abspath("."))

from app.models.project import Project
from app.services.ai.models.scene_direction import SceneDirection
from app.services.ai.models.shot_direction import ShotDirection
from app.services.ai.models.shot_plan import ShotPlan
from app.services.ai.models.character_profile import CharacterProfile, CharacterVisualState
from app.services.ai.builders.prompt_builder import PromptBuilder
from app.services.ai.models.prompt_bundle import PromptBundle
from app.services.ai.exceptions import ValidationError


class TestPromptBuilder(unittest.TestCase):
    """Verify that PromptBuilder builds, compiles, and validates modular prompts correctly."""

    def setUp(self):
        # Sample Project
        self.project = Project(
            id=1,
            title="Anime Test Project",
            video_type="medium",
            target_duration_seconds=60,
            aspect_ratio="16:9",
            language="English",
            art_style="anime"
        )

        # Sample SceneDirection
        self.scene_dir = SceneDirection(
            scene_id=101,
            mood="Mysterious",
            lighting="Dappled forest light",
            primary_focus="Ancient temple ruins",
            camera_style="Fixed",
            composition_rule="Rule of Thirds",
            camera_movement="Static",
            visual_notes="Soft color grading"
        )

        # Sample ShotPlan
        self.shot_plan = ShotPlan(
            scene_id=101,
            shot_number=1,
            shot_type="Wide Shot",
            camera_angle="Eye Level",
            camera_movement="Static",
            composition="Rule of Thirds",
            focus_subject="Ancient temple ruins",
            duration_seconds=5.0,
            transition_in="Fade In",
            transition_out="Cut",
            description="The camera frames the towering stone ruins of the temple.",
            visual_notes="Moss-covered columns."
        )

        # Sample CharacterProfile with visual continuity state
        self.visual_state = CharacterVisualState(
            outfit="wizard robes",
            expression="amazed face",
            pose="holding staff"
        )

        self.char_profile = CharacterProfile(
            character_id=5,
            canonical_name="Kai",
            aliases=["Commander Kai"],
            hair_color="silver",
            hairstyle="messy hair",
            eye_color="blue",
            skin_tone="fair",
            reference_prompt="1boy, silver hair, blue eyes",
            negative_prompt="modern clothing, glasses",
            current_visual_state=self.visual_state
        )

        self.builder = PromptBuilder()

    def test_anime_profile_and_tags_extraction(self):
        bundle = self.builder.build_prompt_bundle(
            self.project,
            self.scene_dir,
            self.shot_plan,
            [self.char_profile]
        )

        # Verify populated PromptBundle fields
        self.assertEqual(bundle.shot_id, "101_1")
        self.assertIn("anime style", bundle.style_tags)
        self.assertIn("masterpiece", bundle.quality_tags)
        self.assertIn("Wide Shot", bundle.camera_tags)
        
        # Verify no fabricated character traits
        self.assertIn("1boy, silver hair, blue eyes, silver hair, messy hair, blue eyes, fair skin, wizard robes, amazed face, holding staff", bundle.character_tags)
        self.assertIn("modern clothing, glasses", bundle.negative_prompt_parts)

    def test_prompt_compilation_and_deduplication(self):
        bundle = self.builder.build_prompt_bundle(
            self.project,
            self.scene_dir,
            self.shot_plan,
            [self.char_profile]
        )

        compiled_pos = bundle.metadata["compiled_positive"]
        compiled_neg = bundle.metadata["compiled_negative"]

        # Check order and tags
        self.assertIn("anime style", compiled_pos)
        self.assertIn("masterpiece", compiled_pos)
        self.assertIn("Wide Shot", compiled_pos)
        self.assertIn("The camera frames the towering stone ruins of the temple.", compiled_pos)

        # Verify duplicate removal (e.g. 'silver hair' present in reference_prompt and hair_color tag)
        words = [w.strip().lower() for w in compiled_pos.split(",")]
        # Assert each unique tag is distinct
        self.assertEqual(len(words), len(set(words)))

    def test_empty_prompt_raises_validation_error(self):
        empty_shot_plan = ShotPlan(
            scene_id=101,
            shot_number=2,
            shot_type="",
            camera_angle="",
            camera_movement="",
            composition="",
            focus_subject="",
            duration_seconds=5.0,
            transition_in="",
            transition_out="",
            description="",
            visual_notes=""
        )
        empty_scene_dir = SceneDirection(
            scene_id=101,
            mood="",
            lighting="",
            primary_focus="",
            camera_style="",
            composition_rule="",
            camera_movement="",
            visual_notes=""
        )

        # Force a style profile with empty values to verify exception trigger
        empty_project = Project(
            id=1,
            title="Empty Project",
            video_type="medium",
            target_duration_seconds=60,
            aspect_ratio="16:9",
            language="English",
            art_style="anime"
        )
        
        # Temporarily clear anime profile definitions for error testing
        from app.services.ai.builders.prompt_builder import PROFILES
        original_anime = PROFILES["anime"]
        PROFILES["anime"] = {
            "style_tags": [],
            "quality_tags": [],
            "technical_tags": [],
            "default_negative": []
        }

        try:
            with self.assertRaises(ValidationError):
                self.builder.build_prompt_bundle(
                    empty_project,
                    empty_scene_dir,
                    empty_shot_plan,
                    []
                )
        finally:
            PROFILES["anime"] = original_anime

    def test_invalid_chars_raises_validation_error(self):
        self.shot_plan.description = "Character holds <sword>."
        with self.assertRaises(ValidationError):
            self.builder.build_prompt_bundle(
                self.project,
                self.scene_dir,
                self.shot_plan,
                [self.char_profile]
            )

    def test_prompt_builder_stage_execution(self):
        from app.services.ai.pipeline.pipeline_context import PipelineContext
        from app.services.ai.stages.prompt_builder_stage import PromptBuilderStage

        context = PipelineContext(project=self.project)
        context.scene_directions = [self.scene_dir]
        context.shot_plans = [self.shot_plan]
        context.character_profiles = {"Kai": self.char_profile}

        # Run the stage
        stage = PromptBuilderStage(db=None)
        updated_context = stage.run(context)

        self.assertIn("prompt_bundles", updated_context.metadata)
        bundles = updated_context.metadata["prompt_bundles"]
        self.assertEqual(len(bundles), 1)
        self.assertEqual(bundles[0].shot_id, "101_1")
        self.assertIn("anime style", bundles[0].metadata["compiled_positive"])


if __name__ == "__main__":
    unittest.main()
