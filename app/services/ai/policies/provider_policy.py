import logging
from typing import List, Dict, Any, Tuple, Optional
from app.core.config import settings
from .quality_mode import QualityMode
from .provider_route import ProviderRoute
from .quality_profile import QualityProfile, QualityProfileConfig, resolve_profile

logger = logging.getLogger("ProviderPolicy")


class ProviderPolicy:
    """Enforces quality preservation policies on provider and model selection.

    Sprint 29.1 Final: Now accepts an optional RenderProfile at the top of the hierarchy.

    Routing hierarchy:
        RenderProfile               (full rendering preset, owns model + quality tier)
            └── QualityProfile      (routing rules: downgrade / fallback)
                    └── ProviderPolicy  (executes the actual route selection)

    Pipeline mode (QualityMode) and QualityProfile/RenderProfile are ORTHOGONAL.
    - Pipeline mode    → development / testing / production  (controls fallback behaviour)
    - QualityProfile   → QuickDraft / Preview / Production / Master  (controls model & params)
    - RenderProfile    → Named preset with full model + step + template configuration
    """

    def __init__(
        self,
        mode: str = "production",
        allow_quality_downgrade: bool = False,
        preferred_model: str = "black-forest-labs/FLUX.1-dev",
        preferred_transport: str = "fal-ai",
        allowed_transports: Optional[List[str]] = None,
        quality_profile: Optional[str] = None,
        render_profile: Optional[Any] = None,   # RenderProfile instance or dict
    ) -> None:
        self.mode = QualityMode(mode.lower())

        # ── RenderProfile takes highest precedence ─────────────────────────
        self.render_profile = None
        if render_profile is not None:
            from .render_profile import RenderProfile
            if isinstance(render_profile, dict):
                render_profile = RenderProfile.from_dict(render_profile)
            self.render_profile = render_profile
            preferred_model       = render_profile.preferred_model
            preferred_transport   = render_profile.preferred_transport
            quality_profile       = render_profile.quality_profile
            # Derive downgrade permission from the quality profile tier
            _qcfg = resolve_profile(quality_profile)
            allow_quality_downgrade = _qcfg.allow_quality_downgrade

        # ── QualityProfile overrides individual params ─────────────────────
        self.quality_profile: Optional[QualityProfileConfig] = None
        if quality_profile:
            self.quality_profile = resolve_profile(quality_profile)
            preferred_model         = self.quality_profile.preferred_model if not self.render_profile else preferred_model
            preferred_transport     = self.quality_profile.preferred_transport if not self.render_profile else preferred_transport
            allow_quality_downgrade = self.quality_profile.allow_quality_downgrade

        self.allow_quality_downgrade = allow_quality_downgrade
        self.preferred_model     = preferred_model
        self.preferred_transport = preferred_transport
        self.allowed_transports  = allowed_transports or ["fal-ai", "huggingface", "comfyui", "mock"]

    # ── Convenience constructors ──────────────────────────────────────────

    @classmethod
    def from_profile(cls, profile: str, mode: str = "production") -> "ProviderPolicy":
        """Build a policy from a QualityProfile name."""
        cfg = resolve_profile(profile)
        return cls(
            mode=mode,
            quality_profile=profile,
            preferred_model=cfg.preferred_model,
            preferred_transport=cfg.preferred_transport,
            allow_quality_downgrade=cfg.allow_quality_downgrade,
        )

    @classmethod
    def from_render_profile(cls, render_profile: Any, mode: str = "production") -> "ProviderPolicy":
        """Build a policy from a RenderProfile instance or name string."""
        from .render_profile import RenderProfile, resolve_render_profile
        if isinstance(render_profile, str):
            render_profile = resolve_render_profile(render_profile)
        return cls(mode=mode, render_profile=render_profile)

    # ── Policy query methods ───────────────────────────────────────────────

    def get_preferred_model(self) -> str:
        return self.preferred_model

    def get_allowed_transports(self, model: str) -> List[str]:
        # RenderProfile MASTER forbids transport fallback
        if self.render_profile is not None:
            qcfg = self.render_profile.resolve_quality_config()
            if not qcfg.allow_transport_fallback:
                return [self.preferred_transport]
        if self.quality_profile and not self.quality_profile.allow_transport_fallback:
            return [self.preferred_transport]
        return self.allowed_transports

    def is_quality_downgrade_allowed(self) -> bool:
        if self.mode == QualityMode.PRODUCTION:
            return False
        return self.allow_quality_downgrade

    def select_route(
        self,
        requested_model: str,
        requested_transport: str,
        available_transports: Dict[str, List[str]],
    ) -> Tuple[str, str, str]:
        """Selects the best route or returns pause/fail action if quality cannot be preserved.

        Rules:
          Production: Never silently downgrade. Same-model transport fallback allowed.
                      Different-model fallback only when explicitly allowed.
          Development: Respect RenderProfile/QualityProfile configuration.
          Testing: Allow configurable overrides.
        """
        profile_label = (
            self.render_profile.name if self.render_profile
            else (self.quality_profile.profile if self.quality_profile else "none")
        )
        logger.info(
            f"Policy evaluation: mode={self.mode.value}, profile={profile_label}, "
            f"requested_model={requested_model}, requested_transport={requested_transport}"
        )

        # Normalize keys
        req_model_lower     = requested_model.lower().strip()
        req_transport_lower = requested_transport.lower().strip()
        normalized_available: Dict[str, List[str]] = {
            m.lower().strip(): [t.lower().strip() for t in tl]
            for m, tl in available_transports.items()
        }

        # 1. Exact match
        if (req_model_lower in normalized_available
                and req_transport_lower in normalized_available[req_model_lower]):
            logger.info(f"Exact route: {requested_model} via {requested_transport}")
            return requested_model, requested_transport, "execute"

        # 2. Transport fallback (same model)
        allow_transport_fallback = True
        if self.render_profile:
            allow_transport_fallback = self.render_profile.resolve_quality_config().allow_transport_fallback
        elif self.quality_profile:
            allow_transport_fallback = self.quality_profile.allow_transport_fallback

        if allow_transport_fallback and req_model_lower in normalized_available and normalized_available[req_model_lower]:
            orig_key = next(k for k in available_transports if k.lower().strip() == req_model_lower)
            fallback_transport = available_transports[orig_key][0]
            logger.info(f"Transport fallback: {orig_key} via {fallback_transport}")
            return orig_key, fallback_transport, "execute"

        # 3. Model downgrade — only if allowed
        if self.is_quality_downgrade_allowed():
            for orig_model_key, transports in available_transports.items():
                m_lower = orig_model_key.lower()
                if "schnell" in m_lower or "mock" in m_lower or "sd" in m_lower:
                    if transports:
                        logger.info(f"Quality downgrade permitted: {orig_model_key} via {transports[0]}")
                        return orig_model_key, transports[0], "execute"

        # 4. Fail closed or pause
        if self.mode == QualityMode.PRODUCTION:
            logger.warning(f"Quality policy violation: {requested_model} is unavailable. Failing closed.")
            return requested_model, requested_transport, "fail"
        else:
            logger.warning(f"Quality policy violation: {requested_model} is unavailable. Pausing.")
            return requested_model, requested_transport, "pause"
