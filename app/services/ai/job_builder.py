"""
Job Builder Service.
"""

import logging
from typing import List
from sqlalchemy.orm import Session
from app.models.scene import Scene
from app.models.generation_job import GenerationJob
from app.services.generation_job import create_jobs_for_scene

logger = logging.getLogger("ai_studio")


class JobBuilder:
    """Service to create generation jobs for a collection of scenes."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def build_jobs(self, scenes: List[Scene]) -> List[GenerationJob]:
        """Build and persist generation jobs for the provided scenes.

        Args:
            scenes: List of Scene ORM objects.

        Returns:
            List of generated and saved GenerationJob ORM objects.
        """
        logger.info(f"Building generation jobs for {len(scenes)} scenes...")
        all_jobs = []
        for scene in scenes:
            logger.info(f"Creating jobs for Scene ID: {scene.id}")
            # By default using 'mock' or setting it based on a provider, or using create_jobs_for_scene
            jobs = create_jobs_for_scene(self.db, scene.id)
            all_jobs.extend(jobs)
        logger.info(f"Successfully built {len(all_jobs)} generation jobs.")
        return all_jobs
