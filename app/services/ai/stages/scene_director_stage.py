"""
Pipeline Stage wrapper for the SceneDirector.
"""

import logging
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.services.ai.stage import PipelineStage
from app.services.ai.pipeline_context import PipelineContext
from app.services.ai.directors.scene_director import SceneDirector

logger = logging.getLogger("ai_studio")


class SceneDirectorStage(PipelineStage):
    """Pipeline stage executing cinematic scene direction planning."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.director = SceneDirector(self.db)

    def run(self, context: PipelineContext) -> PipelineContext:
        """Execute the scene director on the current pipeline context.

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
            # Direct scenes
            self.director.direct_scenes(context)
            logger.info(f"Stage {stage_name} completed scene direction planning successfully.")
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
