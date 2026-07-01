"""
app/services/ai/policies/render_profile.py

RenderProfile — a complete rendering preset that sits above QualityProfile.

Architecture:
    RenderProfile
        └── quality_profile  (QuickDraft / Preview / Production / Master)
        └── preferred_model
        └── preferred_transport
        └── resolution / aspect_ratio / scheduler / steps / guidance_scale
        └── seed_strategy
        └── negative_prompt_template
        └── style_template

Projects reference a RenderProfile by name.
RenderProfiles reference the actual model.
This decouples project configuration from model names, so future model
migrations (e.g., FLUX Dev → successor model) require only updating the
RenderProfile, not every project.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from .quality_profile import QualityProfile, QualityProfileConfig, resolve_profile


@dataclass
class RenderProfile:
    """A complete rendering preset that fully describes how to render an image.

    Projects reference a RenderProfile by name.
    RenderProfiles reference the actual model.
    """
    # ── identity ──────────────────────────────────────────────────────────
    name: str
    description: str = ""

    # ── quality tier (delegates to QualityProfile for routing rules) ──────
    quality_profile: str = QualityProfile.PRODUCTION

    # ── model & transport ──────────────────────────────────────────────────
    preferred_model: str = "black-forest-labs/FLUX.1-dev"
    preferred_transport: str = "fal-ai"

    # ── image parameters ──────────────────────────────────────────────────
    width: int = 1024
    height: int = 576
    aspect_ratio: str = "16:9"
    scheduler: str = "euler"
    steps: int = 50
    guidance_scale: float = 7.5
    seed_strategy: str = "fixed"     # fixed | random | sequential

    # ── prompt templates (None = no template applied) ─────────────────────
    negative_prompt_template: Optional[str] = None
    style_template: Optional[str] = None   # e.g. "anime style, cel-shading, vivid colors"

    metadata: Dict[str, Any] = field(default_factory=dict)

    # ── convenience ───────────────────────────────────────────────────────
    def resolve_quality_config(self) -> QualityProfileConfig:
        """Return the QualityProfileConfig that governs routing / fallback rules."""
        return resolve_profile(self.quality_profile)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RenderProfile":
        return cls(
            name=data.get("name", "custom"),
            description=data.get("description", ""),
            quality_profile=data.get("quality_profile", QualityProfile.PRODUCTION),
            preferred_model=data.get("preferred_model", "black-forest-labs/FLUX.1-dev"),
            preferred_transport=data.get("preferred_transport", "fal-ai"),
            width=data.get("width", 1024),
            height=data.get("height", 576),
            aspect_ratio=data.get("aspect_ratio", "16:9"),
            scheduler=data.get("scheduler", "euler"),
            steps=data.get("steps", 50),
            guidance_scale=data.get("guidance_scale", 7.5),
            seed_strategy=data.get("seed_strategy", "fixed"),
            negative_prompt_template=data.get("negative_prompt_template"),
            style_template=data.get("style_template"),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_quality_profile(cls, quality_profile: str, name: Optional[str] = None) -> "RenderProfile":
        """Migration helper: auto-create a RenderProfile from a QualityProfile name.

        Used when an existing project has no explicit RenderProfile.
        No manual migration required.
        """
        cfg = resolve_profile(quality_profile)
        return cls(
            name=name or f"auto_{quality_profile}",
            description=f"Auto-migrated from QualityProfile({quality_profile})",
            quality_profile=quality_profile,
            preferred_model=cfg.preferred_model,
            preferred_transport=cfg.preferred_transport,
            steps=cfg.generation_steps,
            guidance_scale=cfg.guidance_scale,
        )


# ── Built-in named profiles ────────────────────────────────────────────────

ANIME_NEGATIVE = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, "
    "fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, "
    "signature, watermark, username, blurry"
)

RENDER_PROFILE_REGISTRY: Dict[str, RenderProfile] = {
    "anime_draft": RenderProfile(
        name="anime_draft",
        description="Fast anime iteration — FLUX Schnell, low steps, small resolution",
        quality_profile=QualityProfile.QUICK_DRAFT,
        preferred_model="black-forest-labs/FLUX.1-schnell",
        preferred_transport="huggingface",
        width=512,
        height=288,
        aspect_ratio="16:9",
        scheduler="euler",
        steps=15,
        guidance_scale=3.5,
        seed_strategy="random",
        negative_prompt_template=ANIME_NEGATIVE,
        style_template="anime style, cel-shading, flat colors",
    ),
    "anime_preview": RenderProfile(
        name="anime_preview",
        description="Anime preview — medium quality for client review",
        quality_profile=QualityProfile.PREVIEW,
        preferred_model="black-forest-labs/FLUX.1-schnell",
        preferred_transport="huggingface",
        width=768,
        height=432,
        aspect_ratio="16:9",
        scheduler="euler",
        steps=28,
        guidance_scale=5.0,
        seed_strategy="fixed",
        negative_prompt_template=ANIME_NEGATIVE,
        style_template="anime style, vibrant colors, detailed line art",
    ),
    "anime_production": RenderProfile(
        name="anime_production",
        description="Anime production — FLUX Dev, full quality, no downgrade",
        quality_profile=QualityProfile.PRODUCTION,
        preferred_model="black-forest-labs/FLUX.1-dev",
        preferred_transport="fal-ai",
        width=1024,
        height=576,
        aspect_ratio="16:9",
        scheduler="euler",
        steps=50,
        guidance_scale=7.5,
        seed_strategy="fixed",
        negative_prompt_template=ANIME_NEGATIVE,
        style_template="anime style, cinematic lighting, highly detailed, 4k",
    ),
    "anime_master": RenderProfile(
        name="anime_master",
        description="Anime master — highest quality, 2K, no fallback",
        quality_profile=QualityProfile.MASTER,
        preferred_model="black-forest-labs/FLUX.1-dev",
        preferred_transport="fal-ai",
        width=2048,
        height=1152,
        aspect_ratio="16:9",
        scheduler="euler",
        steps=60,
        guidance_scale=8.5,
        seed_strategy="fixed",
        negative_prompt_template=ANIME_NEGATIVE,
        style_template="anime style, ultra-detailed, cinematic, masterpiece quality, 8k",
    ),
}


def get_render_profile(name: str) -> Optional[RenderProfile]:
    """Look up a named RenderProfile from the built-in registry.

    Returns None if the name is not found — callers should then use
    RenderProfile.from_quality_profile() as a fallback.
    """
    return RENDER_PROFILE_REGISTRY.get(name.lower())


def resolve_render_profile(
    name: Optional[str] = None,
    quality_profile: Optional[str] = None,
) -> RenderProfile:
    """Return a RenderProfile by name, or auto-create one from a QualityProfile.

    Priority:
      1. Named lookup in registry
      2. Auto-create from quality_profile
      3. Default to anime_production
    """
    if name:
        profile = get_render_profile(name)
        if profile:
            return profile
    if quality_profile:
        return RenderProfile.from_quality_profile(quality_profile)
    return RENDER_PROFILE_REGISTRY["anime_production"]
