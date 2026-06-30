"""
ShotDirection model representing a cinematic shot.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ShotDirection:
    """Represents a planned cinematic shot within a scene."""

    shot_number: int
    """Sequential number of the shot in the scene."""

    shot_type: str
    """Framing type (e.g. Wide Shot, Close-up)."""

    camera_angle: str
    """Camera vertical angle (e.g. Eye Level, Low Angle, High Angle)."""

    camera_movement: str
    """Camera kinetic motion (e.g. Pan, Tilt, Dolly, Static)."""

    composition: str
    """Framing/composition rule (e.g. Rule of Thirds, Center Composition)."""

    duration_seconds: float
    """Target duration of the shot in seconds."""

    focus_subject: str
    """Primary subject of visual focus in the frame."""

    description: str
    """Detailed visual description of what is happening in the shot."""

    notes: Optional[str] = None
    """Optional developer or artist notes."""
