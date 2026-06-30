"""
Project Pipeline Orchestrator Service.
"""

import logging
import time
from typing import List
from sqlalchemy.orm import Session

from app.models.project import Project
from app.services.ai.pipeline_context import PipelineContext
from app.services.ai.stage import PipelineStage
from app.services.ai.stages.story_stage import StoryStage
from app.services.ai.stages.scene_director_stage import SceneDirectorStage
from app.services.ai.stages.job_builder_stage import JobBuilderStage
from app.services.ai.production_summary import ProductionSummary

logger = logging.getLogger("ai_studio")


class ProjectPipeline:
    """Orchestrator for the complete project production generation workflow."""

    def __init__(self, db: Session) -> None:
        self.db = db
        # Default registered stages in correct order of execution
        self.stages: List[PipelineStage] = [
            StoryStage(self.db),
            SceneDirectorStage(self.db),
            JobBuilderStage(self.db)
        ]

    def generate_project(self, project_id: int, variables: dict = None) -> ProductionSummary:
        """Run all registered stages sequentially for the given project ID.

        Args:
            project_id: The ID of the project to generate.
            variables: Optional prompt generation variables (e.g. genre, theme).

        Returns:
            ProductionSummary containing pipeline metrics.
        """
        logger.info(f"ProjectPipeline execution started for Project ID: {project_id}")
        t_start = time.perf_counter()
        
        # 1. Load project
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            logger.error(f"Project with ID {project_id} not found.")
            raise ValueError(f"Project with ID {project_id} not found.")

        # 2. Create PipelineContext
        context = PipelineContext(project=project)
        if variables:
            context.metadata["variables"] = variables

        context.status = "running"

        # 3. Execute registered stages
        try:
            for stage in self.stages:
                stage.run(context)
            context.status = "completed"
        except Exception as e:
            logger.error(f"ProjectPipeline failed during execution: {e}")
            context.status = "failed"
            raise

        t_end = time.perf_counter()
        pipeline_duration = t_end - t_start

        # Calculate estimated duration (sum of scene duration_seconds)
        estimated_duration = sum(scene.duration_seconds for scene in context.scenes)

        # 4. Return ProductionSummary
        summary = ProductionSummary(
            project_id=project.id,
            story_id=context.story.id if context.story else None,
            episode_count=len(context.episodes),
            scene_count=len(context.scenes),
            job_count=len(context.generation_jobs),
            estimated_duration=estimated_duration,
            pipeline_duration=pipeline_duration,
            status=context.status
        )
        
        logger.info(
            f"ProjectPipeline execution completed successfully. "
            f"Jobs generated: {summary.job_count}, total scenes: {summary.scene_count}."
        )
        return summary
