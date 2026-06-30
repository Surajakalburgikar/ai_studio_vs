"""
verify_sprint_27.py — Unit and integration tests for Sprint 27 Generation Specification Builder.
"""

import os
import sys
import unittest

# Setup path so app is importable
sys.path.append(os.path.abspath("."))

from app.models.project import Project
from app.services.ai.models.prompt_bundle import PromptBundle
from app.services.ai.builders.generation_specification_builder import GenerationSpecificationBuilder
from app.services.ai.exceptions import ValidationError


class TestGenerationSpecificationBuilder(unittest.TestCase):
    """Verify that GenerationSpecificationBuilder builds, packages, and validates specifications correctly."""

    def setUp(self):
        # Sample Project
        self.project = Project(
            id=1,
            title="Spec Test Project",
            video_type="medium",
            target_duration_seconds=60,
            aspect_ratio="16:9",
            language="English",
            art_style="anime"
        )
        # Mock inject provider/model for testing
        self.project.provider = "flux"
        self.project.model = "flux-dev"
        self.project.generation_steps = 28
        self.project.guidance_scale = 6.5
        self.project.seed = 42

        # Mock PromptBundle
        self.prompt_bundle = PromptBundle(
            shot_id="101_1",
            positive_prompt_parts=["A beautiful landscape"],
            negative_prompt_parts=["blurry", "low quality"],
            style_tags=["anime style"],
            quality_tags=["masterpiece"],
            camera_tags=["Wide Shot"],
            character_tags=[],
            environment_tags=[],
            lighting_tags=[],
            composition_tags=[],
            technical_tags=[]
        )
        # Pre-compile prompts
        self.prompt_bundle.compile_positive_prompt()
        self.prompt_bundle.compile_negative_prompt()

        # Output configuration
        self.output_config = {
            "filename": "shot_101_1.png",
            "format": "png",
            "relative_output_path": "projects/1/shots"
        }

        self.builder = GenerationSpecificationBuilder()

    def test_successful_specification_build(self):
        spec = self.builder.build_specification(
            prompt_bundle=self.prompt_bundle,
            project=self.project,
            output_config=self.output_config,
            job_id="job_spec_101_1"
        )

        self.assertEqual(spec.job_id, "job_spec_101_1")
        self.assertEqual(spec.provider, "flux")
        self.assertEqual(spec.model, "flux-dev")
        self.assertEqual(spec.compiled_positive_prompt, self.prompt_bundle.compile_positive_prompt())
        self.assertEqual(spec.compiled_negative_prompt, self.prompt_bundle.compile_negative_prompt())
        self.assertEqual(spec.generation_parameters["width"], 1024)
        self.assertEqual(spec.generation_parameters["height"], 576)
        self.assertEqual(spec.generation_parameters["seed"], 42)
        self.assertEqual(spec.output_configuration["filename"], "shot_101_1.png")
        self.assertEqual(spec.storage_configuration["storage_provider"], "abstract")
        self.assertEqual(spec.storage_configuration["relative_output_path"], "projects/1/shots")

    def test_mock_provider_selection(self):
        self.project.provider = "mock"
        self.project.model = "mock-model"
        spec = self.builder.build_specification(
            prompt_bundle=self.prompt_bundle,
            project=self.project,
            output_config=self.output_config,
            job_id="job_spec_101_1"
        )
        self.assertEqual(spec.provider, "mock")
        self.assertEqual(spec.model, "mock-model")

    def test_validation_empty_prompt(self):
        # Empty positive prompt
        empty_bundle = PromptBundle(
            shot_id="101_2",
            positive_prompt_parts=[],
            negative_prompt_parts=[]
        )
        empty_bundle.compile_positive_prompt()
        empty_bundle.compile_negative_prompt()

        with self.assertRaises(ValidationError):
            self.builder.build_specification(
                prompt_bundle=empty_bundle,
                project=self.project,
                output_config=self.output_config,
                job_id="job_spec_101_2"
            )

    def test_validation_unsupported_provider(self):
        self.project.provider = "invalid-provider"
        with self.assertRaises(ValidationError):
            self.builder.build_specification(
                prompt_bundle=self.prompt_bundle,
                project=self.project,
                output_config=self.output_config,
                job_id="job_spec_101_1"
            )

    def test_validation_invalid_dimensions(self):
        self.project.seed = -1
        with self.assertRaises(ValidationError):
            self.builder.build_specification(
                prompt_bundle=self.prompt_bundle,
                project=self.project,
                output_config=self.output_config,
                job_id="job_spec_101_1"
            )

    def test_validation_missing_output_path(self):
        bad_config = {
            "filename": "shot_101_1.png",
            "format": "png",
            "relative_output_path": ""
        }
        with self.assertRaises(ValidationError):
            self.builder.build_specification(
                prompt_bundle=self.prompt_bundle,
                project=self.project,
                output_config=bad_config,
                job_id="job_spec_101_1"
            )

    def test_generation_specification_stage_execution(self):
        from app.services.ai.pipeline.pipeline_context import PipelineContext
        from app.services.ai.stages.generation_specification_stage import GenerationSpecificationStage

        context = PipelineContext(project=self.project)
        context.metadata["prompt_bundles"] = [self.prompt_bundle]

        stage = GenerationSpecificationStage(db=None)
        updated_context = stage.run(context)

        self.assertIn("generation_specifications", updated_context.metadata)
        specs = updated_context.metadata["generation_specifications"]
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0].job_id, "job_spec_101_1")
        self.assertEqual(specs[0].provider, "flux")


if __name__ == "__main__":
    unittest.main()
