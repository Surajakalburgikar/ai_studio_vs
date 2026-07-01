from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional

@dataclass
class ProductionCheckpoint:
    continuity_key: str
    project_id: int
    scene_id: int
    last_completed_step: str  # e.g., 'story_generated', 'shot_planned', 'job_completed'
    last_completed_shot_number: int
    last_completed_scene_number: int
    status: str  # e.g., 'active', 'paused', 'completed'
    episode_id: Optional[int] = None
    shot_id: Optional[int] = None
    job_id: Optional[int] = None
    prompt_hash: str = ""
    provider: str = ""
    model: str = ""
    output_path: str = ""
    generation_time: float = 0.0
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductionCheckpoint":
        return cls(
            continuity_key=data["continuity_key"],
            project_id=data["project_id"],
            scene_id=data["scene_id"],
            last_completed_step=data["last_completed_step"],
            last_completed_shot_number=data.get("last_completed_shot_number", 0),
            last_completed_scene_number=data.get("last_completed_scene_number", 0),
            status=data.get("status", "active"),
            episode_id=data.get("episode_id"),
            shot_id=data.get("shot_id"),
            job_id=data.get("job_id"),
            prompt_hash=data.get("prompt_hash", ""),
            provider=data.get("provider", ""),
            model=data.get("model", ""),
            output_path=data.get("output_path", ""),
            generation_time=data.get("generation_time", 0.0),
            retry_count=data.get("retry_count", 0),
            metadata=data.get("metadata", {})
        )
