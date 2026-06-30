"""
CharacterProfile model representing the runtime visual representation of a character.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class CharacterVisualState:
    """Represents the active visual configuration for continuity tracking."""

    outfit: Optional[str] = None
    """Current outfit/clothing state."""

    expression: Optional[str] = None
    """Current facial expression."""

    pose: Optional[str] = None
    """Current stance, posture, or action pose."""

    props: Optional[str] = None
    """Carried items or active scene props in hand."""

    injuries: Optional[str] = None
    """Visual signs of damage (e.g. cuts, bruises, scars)."""

    weather_effects: Optional[str] = None
    """Environmental details affecting appearance (e.g. wet hair, snow on clothes)."""

    temporary_changes: Optional[str] = None
    """Transient physical alterations (e.g. glowing eyes, dirty hands)."""


@dataclass
class CharacterProfile:
    """Canonical visual consistency profile for a recurring character."""

    character_id: int
    """Database identifier of the character."""

    canonical_name: str
    """Normalized, canonical name of the character."""

    aliases: List[str] = field(default_factory=list)
    """List of normalized alternative names or alias references."""

    appearance_summary: Optional[str] = None
    """General description of the character's appearance."""

    hairstyle: Optional[str] = None
    """Hair style parameters (e.g. short crop, ponytail)."""

    hair_color: Optional[str] = None
    """Hair color descriptor (e.g. jet black, blonde)."""

    eye_color: Optional[str] = None
    """Eye color descriptor (e.g. blue, green)."""

    skin_tone: Optional[str] = None
    """Skin tone/color descriptor."""

    body_type: Optional[str] = None
    """Body shape or build (e.g. athletic, slender)."""

    age_group: Optional[str] = None
    """General age classification or age range."""

    default_outfit: Optional[str] = None
    """Primary wardrobe configuration for rendering consistency."""

    accessories: Optional[str] = None
    """Notable items or items regularly carried."""

    expression_defaults: Optional[str] = None
    """Default facial expression configuration."""

    pose_defaults: Optional[str] = None
    """Default pose parameters or posture cues."""

    visual_notes: Optional[str] = None
    """Special styling notes or render parameters."""

    reference_prompt: Optional[str] = None
    """Positive prompt fragment to inject into diffusion generators."""

    negative_prompt: Optional[str] = None
    """Negative prompt fragment to prevent visual drift."""

    scene_history: List[int] = field(default_factory=list)
    """Database identifiers of scenes in which the character appears."""

    shot_history: List[int] = field(default_factory=list)
    """Identifiers/indexes of shots in which the character appears."""

    current_visual_state: CharacterVisualState = field(default_factory=CharacterVisualState)
    """Active visual configuration representing current visual continuity."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Extensible metadata payload for variables or experimental parameters."""
