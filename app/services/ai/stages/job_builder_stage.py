"""
Pipeline Stage for building generation jobs.
"""

import logging
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.services.ai.stage import PipelineStage
from app.services.ai.pipeline_context import PipelineContext
from app.services.ai.job_builder import JobBuilder

logger = logging.getLogger("ai_studio")


class JobBuilderStage(PipelineStage):
    """Pipeline stage that calls the JobBuilder to construct and save GenerationJobs."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.builder = JobBuilder(self.db)

    def run(self, context: PipelineContext) -> PipelineContext:
        """Run the job builder on the scenes inside the context.

        Args:
            context: The shared PipelineContext object.

        Returns:
            The updated PipelineContext object with generation_jobs populated.
        """
        stage_name = self.__class__.__name__
        logger.info(f"Stage {stage_name} started for {len(context.scenes)} scenes.")
        t0 = time.perf_counter()
        
        # Mark timestamp for stage start
        context.timestamps[f"{stage_name}_started"] = datetime.now(timezone.utc)

        try:
            # Build jobs
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
