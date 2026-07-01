from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional


class QualityProfile(str, Enum):
    """Named quality tiers that bundle model + transport + generation parameter defaults.
    
    Pipeline mode (development/testing/production) and QualityProfile are ORTHOGONAL concepts.
    Example: Pipeline=development + Profile=Production is perfectly valid (engineer testing at prod quality).
    """
    QUICK_DRAFT = "quick_draft"    # Fast iteration — schnell, 15-20 steps
    PREVIEW     = "preview"        # Medium quality — fast model, 25-30 steps
    PRODUCTION  = "production"     # Full quality — FLUX dev, 40-50 steps, no downgrade
    MASTER      = "master"         # Highest available — max steps, best provider


@dataclass
class QualityProfileConfig:
    """Runtime configuration bundle resolved from a QualityProfile enum value."""
    profile: str
    preferred_model: str
    preferred_transport: str
    allow_quality_downgrade: bool
    allow_transport_fallback: bool
    max_resolution: int          # max dimension in pixels
    generation_steps: int
    guidance_scale: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QualityProfileConfig":
        return cls(
            profile=data.get("profile", QualityProfile.PRODUCTION),
            preferred_model=data.get("preferred_model", "black-forest-labs/FLUX.1-dev"),
            preferred_transport=data.get("preferred_transport", "huggingface"),
            allow_quality_downgrade=data.get("allow_quality_downgrade", False),
            allow_transport_fallback=data.get("allow_transport_fallback", True),
            max_resolution=data.get("max_resolution", 1024),
            generation_steps=data.get("generation_steps", 50),
            guidance_scale=data.get("guidance_scale", 7.5),
            metadata=data.get("metadata", {}),
        )


# ── Default profile registry ────────────────────────────────────────────────
QUALITY_PROFILE_DEFAULTS: Dict[str, QualityProfileConfig] = {
    QualityProfile.QUICK_DRAFT: QualityProfileConfig(
        profile=QualityProfile.QUICK_DRAFT,
        preferred_model="black-forest-labs/FLUX.1-schnell",
        preferred_transport="huggingface",
        allow_quality_downgrade=True,
        allow_transport_fallback=True,
        max_resolution=512,
        generation_steps=15,
        guidance_scale=3.5,
    ),
    QualityProfile.PREVIEW: QualityProfileConfig(
        profile=QualityProfile.PREVIEW,
        preferred_model="black-forest-labs/FLUX.1-schnell",
        preferred_transport="huggingface",
        allow_quality_downgrade=True,
        allow_transport_fallback=True,
        max_resolution=768,
        generation_steps=28,
        guidance_scale=5.0,
    ),
    QualityProfile.PRODUCTION: QualityProfileConfig(
        profile=QualityProfile.PRODUCTION,
        preferred_model="black-forest-labs/FLUX.1-dev",
        preferred_transport="fal-ai",
        allow_quality_downgrade=False,
        allow_transport_fallback=True,
        max_resolution=1024,
        generation_steps=50,
        guidance_scale=7.5,
    ),
    QualityProfile.MASTER: QualityProfileConfig(
        profile=QualityProfile.MASTER,
        preferred_model="black-forest-labs/FLUX.1-dev",
        preferred_transport="fal-ai",
        allow_quality_downgrade=False,
        allow_transport_fallback=False,
        max_resolution=2048,
        generation_steps=60,
        guidance_scale=8.5,
    ),
}


def resolve_profile(profile: str) -> QualityProfileConfig:
    """Return the default QualityProfileConfig for a given profile name.
    Falls back to PRODUCTION if unrecognized."""
    try:
        key = QualityProfile(profile.lower())
    except ValueError:
        key = QualityProfile.PRODUCTION
    return QUALITY_PROFILE_DEFAULTS[key]
