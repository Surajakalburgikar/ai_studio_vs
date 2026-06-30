"""
ShotPlan model representing an executable visual shot plan.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class ShotPlan:
    """Represents a finalized, executable visual shot configuration ready for rendering."""

    scene_id: int
    """Database identifier of the parent scene."""

    shot_number: int
    """Sequential number of this shot within the scene."""

    shot_type: str
    """Framing type (e.g. Wide Shot, Medium Shot, Close-up)."""

    camera_angle: str
    """Vertical camera placement (e.g. Low Angle, Eye Level, High Angle)."""

    camera_movement: str
    """Motion vector for camera movement (e.g. Pan, Dolly, Static)."""

    composition: str
    """Composition framing rule (e.g. Rule of Thirds, Center Composition)."""

    focus_subject: str
    """Main object or actor of interest in the shot."""

    duration_seconds: float
    """Target duration in seconds."""

    transition_in: str
    """Transition style entering the shot (e.g. Cut, Fade In, Dissolve)."""

    transition_out: str
    """Transition style exiting the shot (e.g. Cut, Fade Out, Dissolve)."""

    description: str
    """Detailed visual description of the action and environment."""

    visual_notes: str
    """Color grading, lighting, or style suggestions."""

    scene_direction_id: Optional[int] = None
    """Optional database identifier of the associated SceneDirection."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Extensible metadata dictionary for config flags or model variables."""
