"""
Pipeline Stage for building generation jobs.
"""

import logging
import os
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.services.ai.pipeline.stage import PipelineStage
from app.services.ai.pipeline.pipeline_context import PipelineContext
from app.services.ai.builders.job_builder import JobBuilder

logger = logging.getLogger("ai_studio")


class JobBuilderStage(PipelineStage):
    """Pipeline stage that calls the JobBuilder to construct and save GenerationJobs."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.builder = JobBuilder(self.db)

    def run(self, context: PipelineContext) -> PipelineContext:
        """Run the job builder on the scenes or specifications inside the context.

        Args:
            context: The shared PipelineContext object.

        Returns:
            The updated PipelineContext object with generation_jobs populated.
        """
        stage_name = self.__class__.__name__
        logger.info(f"Stage {stage_name} started.")
        t0 = time.perf_counter()
        
        # Mark timestamp for stage start
        context.timestamps[f"{stage_name}_started"] = datetime.now(timezone.utc)

        try:
            # Check if we have generation specifications
            specs = context.metadata.get("generation_specifications", [])
            provider_val = getattr(context.project, "provider", None) or os.getenv("IMAGE_GENERATOR_PROVIDER")
            if not specs and provider_val in ["flux", "mock"]:
                logger.info("Automatically running GenerationSpecificationStage to generate specifications...")
                from app.services.ai.stages.generation_specification_stage import GenerationSpecificationStage
                spec_stage = GenerationSpecificationStage(self.db)
                spec_stage.run(context)
                specs = context.metadata.get("generation_specifications", [])

            if specs:
                logger.info(f"Building generation jobs from {len(specs)} specifications...")
                from app.services.generation_job import create_job_from_spec
                jobs = []
                for spec in specs:
                    job = create_job_from_spec(self.db, spec)
                    jobs.append(job)
            else:
                logger.info(f"Fallback: building generation jobs for {len(context.scenes)} scenes...")
                # Build jobs from scenes
                jobs = self.builder.build_jobs(context.scenes)
                
            context.generation_jobs = jobs
            logger.info(f"Stage {stage_name} succeeded. Created {len(jobs)} generation jobs.")
        except Exception as e:
            logger.error(f"Stage {stage_name} failed: {e}")
            context.errors.append(f"{stage_name} failed: {str(e)}")
            context.status = "failed"
            raise e
        finally:
            duration = time.perf_counter() - t0
            context.timestamps[f"{stage_name}_completed"] = datetime.now(timezone.utc)
            logger.info(f"Stage {stage_name} completed in {duration:.4f} seconds.")
            logger.info(f"Stage {stage_name} warnings: {context.warnings}")
            logger.info(f"Stage {stage_name} errors: {context.errors}")

        return context
