"""
Pipeline Stage for building generation specifications.
"""

import logging
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.services.ai.pipeline.stage import PipelineStage
from app.services.ai.pipeline.pipeline_context import PipelineContext
from app.services.ai.builders.generation_specification_builder import GenerationSpecificationBuilder

logger = logging.getLogger("ai_studio")


class GenerationSpecificationStage(PipelineStage):
    """Pipeline stage that calls GenerationSpecificationBuilder to create specs for the worker."""

    def __init__(self, db: Session, allowed_providers: list = None) -> None:
        self.db = db
        self.builder = GenerationSpecificationBuilder(allowed_providers=allowed_providers)

    def run(self, context: PipelineContext) -> PipelineContext:
        stage_name = self.__class__.__name__
        logger.info(f"Stage {stage_name} started.")
        t0 = time.perf_counter()

        context.timestamps[f"{stage_name}_started"] = datetime.now(timezone.utc)

        try:
            # 1. Retrieve prompt bundles
            prompt_bundles = context.metadata.get("prompt_bundles", [])
            if not prompt_bundles:
                logger.warning("No prompt bundles found in context metadata. Attempting fallback generation.")
                from app.services.ai.stages.prompt_builder_stage import PromptBuilderStage
                prompt_builder_stage = PromptBuilderStage(self.db)
                prompt_builder_stage.run(context)
                prompt_bundles = context.metadata.get("prompt_bundles", [])

            # 2. Build GenerationSpecifications
            generation_specs = []
            for bundle in prompt_bundles:
                filename = f"shot_{bundle.shot_id}.png"
                output_config = {
                    "filename": filename,
                    "format": "png",
                    "relative_output_path": f"projects/{context.project.id}/shots"
                }
                job_id = f"job_spec_{bundle.shot_id}"

                spec = self.builder.build_specification(
                    prompt_bundle=bundle,
                    project=context.project,
                    output_config=output_config,
                    job_id=job_id
                )
                generation_specs.append(spec)

            # Store in context metadata
            context.metadata["generation_specifications"] = generation_specs
            logger.info(f"Stage {stage_name} succeeded. Created {len(generation_specs)} generation specifications.")

        except Exception as e:
            logger.error(f"Stage {stage_name} failed: {e}")
            context.errors.append(f"{stage_name} failed: {str(e)}")
            context.status = "failed"
            raise e
        finally:
            duration = time.perf_counter() - t0
            context.timestamps[f"{stage_name}_completed"] = datetime.now(timezone.utc)
            logger.info(f"Stage {stage_name} completed in {duration:.4f} seconds.")

        return context
