"""
GenerationSpecification model representing the complete pipeline-to-worker payload schema.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from app.services.ai.models.prompt_bundle import PromptBundle


@dataclass
class GenerationSpecification:
    """Canonical contract containing all generation instructions sent to the worker."""

    job_id: str
    """Unique generation job identifier."""

    provider: str
    """Target generation provider (e.g. 'flux', 'fal_ai', 'gemini')."""

    model: str
    """Specific model name/version to execute (e.g. 'flux-schnell', 'imagen-3')."""

    prompt_bundle: PromptBundle
    """Modular prompt components containing style, camera, and character details."""

    compiled_positive_prompt: str = ""
    """Fully compiled positive prompt string."""

    compiled_negative_prompt: str = ""
    """Fully compiled negative prompt string."""

    generation_parameters: Dict[str, Any] = field(default_factory=dict)
    """Engine-specific parameters (e.g. width, height, steps, guidance_scale, seed)."""

    output_configuration: Dict[str, Any] = field(default_factory=dict)
    """Target file format, resolution, aspect ratio settings."""

    storage_configuration: Dict[str, Any] = field(default_factory=dict)
    """Upload instructions (e.g. bucket, folder path, storage provider)."""

    version: str = "1.0"
    """Schema version descriptor for future-proofing worker parsers."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Extensible execution metadata (timestamps, lease details, retry history)."""
