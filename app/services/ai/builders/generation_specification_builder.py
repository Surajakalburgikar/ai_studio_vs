"""
GenerationSpecificationBuilder engine to package PromptBundles into execution payloads for worker agents.
"""

import logging
import os
from typing import Dict, Any, List, Optional

from app.models.project import Project
from app.services.ai.models.prompt_bundle import PromptBundle
from app.services.ai.models.generation_specification import GenerationSpecification
from app.services.ai.exceptions import ValidationError

logger = logging.getLogger("ai_studio")


class GenerationSpecificationBuilder:
    """Builder class that builds and validates GenerationSpecification payloads."""

    def __init__(self, allowed_providers: Optional[List[str]] = None) -> None:
        # Task 5: Allow configurable providers, default to ['flux', 'mock']
        self.allowed_providers = [
            p.lower() for p in (allowed_providers or ["flux", "mock"])
        ]

    def build_specification(
        self,
        prompt_bundle: PromptBundle,
        project: Project,
        output_config: Dict[str, Any],
        job_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> GenerationSpecification:
        """Constructs a complete GenerationSpecification payload.

        Args:
            prompt_bundle: Compiled prompt details.
            project: Project configuration.
            output_config: Output settings (format, filename, path).
            job_id: Unique generation job identifier.
            metadata: Optional execution metadata overrides.

        Returns:
            Validated GenerationSpecification instance.
        """
        logger.info("GenerationSpecification build started.")

        # 1. Compile prompts using PromptBundle methods
        # Task 4: Do not duplicate prompt compilation logic
        pos_prompt = prompt_bundle.compile_positive_prompt()
        neg_prompt = prompt_bundle.compile_negative_prompt()
        logger.info("Prompt compiled.")

        # 2. Select Provider
        # Task 5: Provider Selection from Project configuration / env overrides
        provider_val = getattr(project, "provider", None)
        if not provider_val:
            provider_val = os.getenv("IMAGE_GENERATOR_PROVIDER", "flux")
        provider = str(provider_val).lower().strip()
        logger.info(f"Provider selected: {provider}")

        # Determine Model
        model_val = getattr(project, "model", None)
        if not model_val:
            model_val = "flux-dev" if provider == "flux" else "mock-model"
        model = str(model_val).lower().strip()

        # 3. Generation Parameters
        # Task 6: Populate width, height, steps, guidance_scale, seed, aspect_ratio
        aspect_ratio = str(project.aspect_ratio or "16:9")
        
        # Map aspect ratio to standard resolution dimensions
        if aspect_ratio == "16:9":
            width, height = 1024, 576
        elif aspect_ratio == "9:16":
            width, height = 576, 1024
        elif aspect_ratio == "1:1":
            width, height = 1024, 1024
        else:
            width, height = 1024, 576

        steps = getattr(project, "generation_steps", 28)
        guidance_scale = getattr(project, "guidance_scale", 6.5)
        seed = getattr(project, "seed", 42)

        gen_params = {
            "width": width,
            "height": height,
            "steps": steps,
            "guidance_scale": guidance_scale,
            "seed": seed,
            "aspect_ratio": aspect_ratio
        }

        # 4. Output and Storage Configuration
        # Task 7: Populate filename, format, relative_output_path abstractly
        filename = output_config.get("filename")
        file_format = output_config.get("format", "png")
        relative_output_path = output_config.get("relative_output_path")

        out_config = {
            "filename": filename,
            "format": file_format,
            "aspect_ratio": aspect_ratio
        }

        storage_config = {
            "storage_provider": "abstract",
            "relative_output_path": relative_output_path,
            "filename": filename
        }
        logger.info("Output configured.")

        # 5. Validation Rules
        # Task 8: Reject empty prompt, unsupported provider, invalid dimensions, invalid seed, missing output path
        if not pos_prompt.strip():
            raise ValidationError("Compiled positive prompt is empty.")

        if provider not in self.allowed_providers:
            raise ValidationError(f"Unsupported provider: '{provider}'. Allowed: {self.allowed_providers}")

        if width <= 0 or height <= 0:
            raise ValidationError(f"Invalid dimensions: {width}x{height}")

        if seed < 0:
            raise ValidationError(f"Invalid seed value: {seed}")

        if not relative_output_path:
            raise ValidationError("Missing relative output path in output configuration.")

        # 6. Build final Specification payload
        spec = GenerationSpecification(
            job_id=job_id,
            provider=provider,
            model=model,
            prompt_bundle=prompt_bundle,
            compiled_positive_prompt=pos_prompt,
            compiled_negative_prompt=neg_prompt,
            generation_parameters=gen_params,
            output_configuration=out_config,
            storage_configuration=storage_config,
            version="1.0",
            metadata=metadata or {}
        )

        logger.info("GenerationSpecification created.")
        return spec
