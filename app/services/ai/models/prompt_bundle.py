"""
PromptBundle model representing modular components of positive and negative prompts.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class PromptBundle:
    """Modular collection of prompt elements for visual generation."""

    shot_id: str
    """Unique identifier for the shot associated with this prompt bundle."""

    positive_prompt_parts: List[str] = field(default_factory=list)
    """Modular positive prompt fragments."""

    negative_prompt_parts: List[str] = field(default_factory=list)
    """Modular negative prompt fragments."""

    style_tags: List[str] = field(default_factory=list)
    """Style-related tags (e.g. 'anime', 'photorealistic')."""

    quality_tags: List[str] = field(default_factory=list)
    """Quality enhancers (e.g. 'masterpiece', 'hyperdetailed')."""

    camera_tags: List[str] = field(default_factory=list)
    """Camera framing and movement modifiers (e.g. 'low angle', 'tracking shot')."""

    character_tags: List[str] = field(default_factory=list)
    """Visual attributes of characters present in the shot."""

    environment_tags: List[str] = field(default_factory=list)
    """Background and setting tags."""

    lighting_tags: List[str] = field(default_factory=list)
    """Lighting setup tags (e.g. 'dappled light', 'cinematic lighting')."""

    composition_tags: List[str] = field(default_factory=list)
    """Composition and framing rule tags."""

    technical_tags: List[str] = field(default_factory=list)
    """Technical/engine-specific tags."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Extensible metadata payload."""

    def compile_positive_prompt(self) -> str:
        """Helper to assemble the positive prompt components into a single string.

        Returns:
            Concatenated positive prompt string.
        """
        all_parts = (
            self.positive_prompt_parts
            + self.style_tags
            + self.quality_tags
            + self.camera_tags
            + self.character_tags
            + self.environment_tags
            + self.lighting_tags
            + self.composition_tags
            + self.technical_tags
        )
        return ", ".join([p.strip() for p in all_parts if p and p.strip()])

    def compile_negative_prompt(self) -> str:
        """Helper to assemble the negative prompt components into a single string.

        Returns:
            Concatenated negative prompt string.
        """
        return ", ".join([n.strip() for n in self.negative_prompt_parts if n and n.strip()])
