"""
Camera Language enums for motion planning.
"""

from enum import Enum


class CameraMovement(str, Enum):
    """Supported camera movements for scenes."""

    PAN = "Pan"
    TILT = "Tilt"
    ZOOM = "Zoom"
    DOLLY = "Dolly"
    STATIC = "Static"
    ORBIT = "Orbit"
