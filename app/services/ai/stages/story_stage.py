"""
Pipeline Stage for generating Story, Episodes, and Scenes.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.services.ai.pipeline.stage import PipelineStage
from app.services.ai.pipeline.pipeline_context import PipelineContext

logger = logging.getLogger("ai_studio")


class StoryStage(PipelineStage):
    """Pipeline stage that calls the AI StoryGenerator to generate story structure."""

    def __init__(self, db: Session) -> None:
        self.db = db
        from app.services.ai.generators.story_generator import StoryGenerator
        self.generator = StoryGenerator(self.db)

    def run(self, context: PipelineContext) -> PipelineContext:
        """Run the story generator on the current project context.

        Args:
            context: The shared PipelineContext object.

        Returns:
            The updated PipelineContext object with story, episodes, and scenes populated.
        """
        stage_name = self.__class__.__name__
        logger.info(f"Stage {stage_name} started for Project ID: {context.project.id}")
        t0 = time.perf_counter()
        
        # Mark timestamp for stage start
        context.timestamps[f"{stage_name}_started"] = datetime.now(timezone.utc)

        # Build variables dict. Merge metadata["variables"] with project configurations.
        variables: Dict[str, Any] = {}
        if "variables" in context.metadata:
            variables.update(context.metadata["variables"])
        else:
            variables.update(context.metadata)

        # Ensure required keys exist with default values if not explicitly set
        defaults = {
            "genre": "General",
            "theme": context.project.description or "General theme",
            "art_style": context.project.art_style.value if hasattr(context.project.art_style, "value") else str(context.project.art_style),
            "audience": "general",
            "language": context.project.language,
            "target_duration": str(context.project.target_duration_seconds),
            "episode_count": "1",
            "episode_duration": str(context.project.target_duration_seconds)
        }
        for key, val in defaults.items():
            if key not in variables or not variables[key]:
                variables[key] = val

        try:
            # Generate the story
            story = self.generator.generate(context.project.id, variables)
            
            # Populate context
            context.story = story
            context.episodes = story.episodes
            
            # Gather all scenes across all episodes
            scenes = []
            for ep in story.episodes:
                scenes.extend(ep.scenes)
            context.scenes = scenes
            
            logger.info(
                f"Stage {stage_name} succeeded. Generated Story ID: {story.id}, "
                f"{len(context.episodes)} episodes, {len(context.scenes)} scenes."
            )
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
