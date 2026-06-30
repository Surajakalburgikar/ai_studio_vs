"""
Composition Rules enums for framing.
"""

from enum import Enum


class CompositionRule(str, Enum):
    """Supported framing and composition rules for camera shots."""

    RULE_OF_THIRDS = "Rule of Thirds"
    LEADING_LINES = "Leading Lines"
    CENTER_COMPOSITION = "Center Composition"
    NEGATIVE_SPACE = "Negative Space"
    FOREGROUND_FRAMING = "Foreground Framing"
