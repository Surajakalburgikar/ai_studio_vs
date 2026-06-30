"""
Pipeline Stage wrapper for the ShotPlanner.
"""

import logging
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.services.ai.pipeline.stage import PipelineStage
from app.services.ai.pipeline.pipeline_context import PipelineContext
from app.services.ai.planners.shot_planner import ShotPlanner

logger = logging.getLogger("ai_studio")


class ShotPlannerStage(PipelineStage):
    """Pipeline stage executing visual shot planning."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.planner = ShotPlanner()

    def run(self, context: PipelineContext) -> PipelineContext:
        """Execute the shot planner on the current pipeline context.

        Args:
            context: Shared PipelineContext.

        Returns:
            Updated PipelineContext.
        """
        stage_name = self.__class__.__name__
        logger.info(f"Stage {stage_name} started.")
        t0 = time.perf_counter()

        # Mark timestamp for stage start
        context.timestamps[f"{stage_name}_started"] = datetime.now(timezone.utc)

        try:
            # Plan shots from scene directions
            shot_plans = self.planner.plan_shots(context.scene_directions)
            context.shot_plans = shot_plans
            logger.info(f"Stage {stage_name} completed shot planning successfully.")
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
