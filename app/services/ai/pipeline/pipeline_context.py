"""
Pipeline Context to pass state across execution stages.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.models.project import Project
from app.models.story import Story
from app.models.episode import Episode
from app.models.scene import Scene
from app.models.generation_job import GenerationJob
from app.services.ai.models.scene_direction import SceneDirection
from app.services.ai.models.shot_plan import ShotPlan


@dataclass
class PipelineContext:
    """Stores execution state and outputs across all pipeline stages."""

    project: Project
    story: Optional[Story] = None
    episodes: List[Episode] = field(default_factory=list)
    scenes: List[Scene] = field(default_factory=list)
    scene_directions: List[SceneDirection] = field(default_factory=list)
    shot_plans: List[ShotPlan] = field(default_factory=list)
    generation_jobs: List[GenerationJob] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    status: str = "pending"
    timestamps: Dict[str, datetime] = field(default_factory=dict)
