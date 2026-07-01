from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass
class ContinuitySnapshot:
    continuity_key: str
    project_id: int
    active_character_states: Dict[str, Any] = field(default_factory=dict)
    active_world_state: Dict[str, Any] = field(default_factory=dict)
    canonical_facts: List[str] = field(default_factory=list)
    timestamp: float = 0.0
