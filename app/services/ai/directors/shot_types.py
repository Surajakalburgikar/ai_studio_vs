"""
Shot Types enums for camera composition and planning.
"""

from enum import Enum


class ShotType(str, Enum):
    """Supported shot framing styles for scenes."""

    WIDE = "Wide Shot"
    MEDIUM = "Medium Shot"
    CLOSE_UP = "Close-up"
    EXTREME_CLOSE_UP = "Extreme Close-up"
    OVER_SHOULDER = "Over Shoulder"
    POV = "POV"
    TRACKING = "Tracking"
    ESTABLISHING = "Establishing"
