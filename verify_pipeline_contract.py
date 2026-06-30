"""
verify_pipeline_contract.py — Validation test verifying the data-flow contract between pipeline stages.
"""

import os
import sys
import unittest

# Setup path so app is importable
sys.path.append(os.path.abspath("."))

from app.models.project import Project
from app.models.story import Story
from app.services.ai.models.scene_direction import SceneDirection
from app.services.ai.models.shot_direction import ShotDirection
from app.services.ai.models.shot_plan import ShotPlan
from app.services.ai.models.character_profile import CharacterProfile, CharacterVisualState
from app.services.ai.models.prompt_bundle import PromptBundle
from app.services.ai.models.generation_specification import GenerationSpecification


class TestPipelineContract(unittest.TestCase):
    """Verifies that all pipeline dataclasses conform to the established interfaces and have no circular imports."""

    def test_pipeline_data_flow_linkage(self):
        # 1. Project Instance
        project = Project(
            id=1,
            title="Contract Test Project",
            video_type="medium",
            target_duration_seconds=60,
            aspect_ratio="16:9",
            language="English"
        )
        self.assertEqual(project.id, 1)

        # 2. Story Instance
        story = Story(
            id=10,
            project_id=project.id,
            title="Contract Test Story",
            genre="Sci-Fi",
            summary="A short summary.",
            story_text="Some text."
        )
        self.assertEqual(story.project_id, project.id)

        # 3. SceneDirection Instance
        sd = SceneDirection(
            scene_id=100,
            mood="Dramatic",
            lighting="Neon lighting",
            primary_focus="Character face",
            camera_style="Cinematic",
            composition_rule="Rule of Thirds",
            camera_movement="Static",
            visual_notes="Moody atmosphere.",
            suggested_shots=[
                ShotDirection(
                    shot_number=1,
                    shot_type="Close-up",
                    camera_angle="Eye Level",
                    camera_movement="Static",
                    composition="Center Composition",
                    duration_seconds=5.0,
                    focus_subject="Character face",
                    description="He stood in silence."
                )
            ],
            estimated_duration=5.0
        )
        self.assertEqual(sd.scene_id, 100)

        # 4. ShotPlan Instance
        shot_plan = ShotPlan(
            scene_id=sd.scene_id,
            shot_number=sd.suggested_shots[0].shot_number,
            shot_type=sd.suggested_shots[0].shot_type,
            camera_angle=sd.suggested_shots[0].camera_angle,
            camera_movement=sd.suggested_shots[0].camera_movement,
            composition=sd.suggested_shots[0].composition,
            focus_subject=sd.suggested_shots[0].focus_subject,
            duration_seconds=sd.suggested_shots[0].duration_seconds,
            transition_in="Fade In",
            transition_out="Cut",
            description="Character is shown in a tight close-up under neon lighting.",
            visual_notes=sd.lighting,
            scene_direction_id=None
        )
        self.assertEqual(shot_plan.scene_id, sd.scene_id)
        self.assertEqual(shot_plan.shot_number, 1)

        # 5. CharacterProfile Instance
        visual_state = CharacterVisualState(
            outfit="Cyberpunk armor",
            expression="Stoic",
            pose="Standing guard",
            props="Katana",
            injuries="Scar on left cheek",
            weather_effects="Rain dripping",
            temporary_changes="Glowing blue cybernetic eye"
        )

        profile = CharacterProfile(
            character_id=50,
            canonical_name="Zara",
            aliases=["Agent Zara"],
            appearance_summary="An agent wearing armor.",
            hairstyle="Buzzcut",
            hair_color="Neon pink",
            eye_color="Blue",
            skin_tone="Pale",
            body_type="Athletic",
            age_group="Adult",
            default_outfit="Armor",
            accessories="Katana",
            expression_defaults="Stoic",
            pose_defaults="Standing",
            visual_notes="Cybernetic accents.",
            reference_prompt="1girl, solo, pink hair, cybernetic eye",
            negative_prompt="blurry, low quality",
            scene_history=[sd.scene_id],
            shot_history=[shot_plan.shot_number],
            current_visual_state=visual_state,
            metadata={"status": "approved"}
        )
        self.assertEqual(profile.character_id, 50)
        self.assertEqual(profile.current_visual_state.outfit, "Cyberpunk armor")

        # 6. PromptBundle Instance
        prompt_bundle = PromptBundle(
            shot_id=f"{sd.scene_id}_{shot_plan.shot_number}",
            positive_prompt_parts=["A futuristic warrior stands guard in the pouring rain."],
            negative_prompt_parts=["worst quality, normal quality, lowres"],
            style_tags=["cyberpunk style", "anime key visual"],
            quality_tags=["masterpiece", "8k resolution"],
            camera_tags=[shot_plan.shot_type, shot_plan.camera_angle, shot_plan.camera_movement],
            character_tags=[profile.reference_prompt, profile.current_visual_state.outfit, profile.current_visual_state.expression],
            environment_tags=["neon wet streets", "high-tech towers"],
            lighting_tags=[sd.lighting],
            composition_tags=[shot_plan.composition],
            technical_tags=["octane render", "unreal engine 5 style"]
        )

        compiled_positive = prompt_bundle.compile_positive_prompt()
        self.assertIn("Close-up", compiled_positive)
        self.assertIn("cyberpunk style", compiled_positive)
        self.assertIn("Cyberpunk armor", compiled_positive)

        # 7. GenerationSpecification Instance
        gen_spec = GenerationSpecification(
            job_id="job_zara_scene_100_shot_1",
            provider="flux",
            model="flux-dev",
            prompt_bundle=prompt_bundle,
            generation_parameters={
                "width": 1024,
                "height": 576,
                "num_inference_steps": 28,
                "guidance_scale": 6.5,
                "seed": 42
            },
            output_configuration={
                "format": "png",
                "quality": 100
            },
            storage_configuration={
                "provider": "s3",
                "bucket": "ai-studio-assets",
                "path": "projects/1/images/job_zara_scene_100_shot_1.png"
            },
            version="1.0",
            metadata={
                "created_at": "2026-06-30T18:00:00Z"
            }
        )

        self.assertEqual(gen_spec.job_id, "job_zara_scene_100_shot_1")
        self.assertEqual(gen_spec.version, "1.0")
        self.assertEqual(gen_spec.prompt_bundle.shot_id, "100_1")


if __name__ == "__main__":
    unittest.main()
