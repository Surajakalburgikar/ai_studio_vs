from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional

@dataclass
class ContinuityManifest:
    continuity_key: str
    series_title: str = ""
    universe_title: str = ""
    continuity_version: int = 1
    current_arc: str = ""
    current_part: str = ""
    canonical_characters: Dict[str, Any] = field(default_factory=dict)
    canonical_locations: Dict[str, Any] = field(default_factory=dict)
    canonical_facts: List[str] = field(default_factory=list)
    timeline_anchor: Dict[str, Any] = field(default_factory=dict)
    last_project_id: Optional[int] = None
    last_episode_number: Optional[int] = None
    last_scene_number: Optional[int] = None
    last_shot_number: Optional[int] = None
    active_character_states: Dict[str, Any] = field(default_factory=dict)
    active_world_state: Dict[str, Any] = field(default_factory=dict)
    preferred_model_profile: Dict[str, Any] = field(default_factory=dict)
    preferred_provider_profile: Dict[str, Any] = field(default_factory=dict)
    quality_policy: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContinuityManifest":
        return cls(
            continuity_key=data["continuity_key"],
            series_title=data.get("series_title", ""),
            universe_title=data.get("universe_title", ""),
            continuity_version=data.get("continuity_version", 1),
            current_arc=data.get("current_arc", ""),
            current_part=data.get("current_part", ""),
            canonical_characters=data.get("canonical_characters", {}),
            canonical_locations=data.get("canonical_locations", {}),
            canonical_facts=data.get("canonical_facts", []),
            timeline_anchor=data.get("timeline_anchor", {}),
            last_project_id=data.get("last_project_id"),
            last_episode_number=data.get("last_episode_number"),
            last_scene_number=data.get("last_scene_number"),
            last_shot_number=data.get("last_shot_number"),
            active_character_states=data.get("active_character_states", {}),
            active_world_state=data.get("active_world_state", {}),
            preferred_model_profile=data.get("preferred_model_profile", {}),
            preferred_provider_profile=data.get("preferred_provider_profile", {}),
            quality_policy=data.get("quality_policy", {}),
            metadata=data.get("metadata", {})
        )
