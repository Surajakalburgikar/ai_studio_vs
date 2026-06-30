"""
Production Summary Dataclass.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProductionSummary:
    """Contains the execution summary metrics of a project pipeline run."""

    project_id: int
    story_id: Optional[int]
    episode_count: int
    scene_count: int
    job_count: int
    estimated_duration: float
    pipeline_duration: float
    status: str
