"""
SceneDirection model representing high-level cinematic direction for a scene.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from .shot_direction import ShotDirection


@dataclass
class SceneDirection:
    """Contains full cinematic planning and shot lists for a specific scene."""

    scene_id: int
    """Unique database identifier of the scene."""

    mood: str
    """Emotional theme or tone of the scene (e.g. Mysterious, Tense)."""

    lighting: str
    """Lighting strategy (e.g. High-key, Low-key, Dramatic)."""

    primary_focus: str
    """Main narrative focus (e.g. Character reaction, Object)."""

    camera_style: str
    """Overall camera design (e.g. Handheld, Steady, Smooth tracking)."""

    composition_rule: str
    """Prevalent composition rule used in the scene framing."""

    camera_movement: str
    """Prevalent camera movement pattern in the scene."""

    visual_notes: str
    """Color grading or aesthetic tips."""

    suggested_shots: List[ShotDirection] = field(default_factory=list)
    """Ordered collection of planned cinematic shots for the scene."""

    estimated_duration: float = 0.0
    """Estimated duration of the scene in seconds (calculated from shots)."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Extensible metadata dictionary for future tags and config variables."""
