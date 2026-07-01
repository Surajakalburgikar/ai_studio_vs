from typing import Dict, Any, List, Optional
from .continuity_manifest import ContinuityManifest
from .canonical_character import CanonicalCharacter, CharacterState, CharacterProfile


class ContinuityResolver:
    """Resolves continuity assets, facts, locations, and configs from a ContinuityManifest.
    
    Sprint 29.1: now understands the CanonicalCharacter / CharacterState split.
    Canonical identity is NEVER overwritten when runtime state changes.
    """

    def resolve_characters(
        self,
        manifest: ContinuityManifest,
        project_characters: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Merge canonical character data from the manifest with current project characters.
        
        Only runtime-state fields (outfit, pose, expression …) may be overridden by the
        scene-level data.  Canonical identity fields (appearance, species, etc.) come
        exclusively from the manifest.
        """
        resolved = []
        canonical_raw = manifest.canonical_characters or {}

        for char in project_characters:
            name = char.get("name", "")
            if name and name in canonical_raw:
                canon_data = canonical_raw[name]
                # Build CanonicalCharacter from stored data (identity is immutable)
                canon = CanonicalCharacter.from_dict(canon_data)
                # Build a CharacterProfile: identity from manifest, state from scene data
                state_data = {
                    "current_outfit":     char.get("clothing", char.get("current_outfit", "")),
                    "current_expression": char.get("current_expression", "neutral"),
                    "current_pose":       char.get("current_pose", ""),
                    "current_location":   char.get("current_location", ""),
                    "current_weapon":     char.get("current_weapon", ""),
                    "accessories":        char.get("accessories", []),
                    "temporary_effects":  char.get("temporary_effects", []),
                    "injuries":           char.get("injuries", []),
                }
                profile = CharacterProfile(
                    identity=canon,
                    current_state=CharacterState.from_dict(state_data),
                )
                resolved.append(profile.to_dict())
            else:
                resolved.append(char)
        return resolved

    def get_canonical_character(
        self,
        manifest: ContinuityManifest,
        character_name: str,
    ) -> Optional[CanonicalCharacter]:
        """Return the canonical identity for a character, or None if not registered."""
        raw = (manifest.canonical_characters or {}).get(character_name)
        if raw is None:
            return None
        return CanonicalCharacter.from_dict(raw)

    def get_character_state(
        self,
        manifest: ContinuityManifest,
        character_name: str,
    ) -> Optional[CharacterState]:
        """Return the last-known runtime state for a character, or None."""
        raw = (manifest.active_character_states or {}).get(character_name)
        if raw is None:
            return None
        return CharacterState.from_dict(raw)

    def update_character_state(
        self,
        manifest: ContinuityManifest,
        character_name: str,
        **state_kwargs,
    ) -> None:
        """Update ONLY the runtime state of a character.  Canonical identity is untouched."""
        existing = manifest.active_character_states.get(character_name, {})
        state = CharacterState.from_dict(existing)
        state_dict = state.to_dict()
        for k, v in state_kwargs.items():
            if k in state_dict:
                state_dict[k] = v
        manifest.active_character_states[character_name] = state_dict

    def resolve_world_facts(self, manifest: ContinuityManifest) -> List[str]:
        return manifest.canonical_facts or []

    def resolve_locations(self, manifest: ContinuityManifest) -> Dict[str, Any]:
        return manifest.canonical_locations or {}

    def apply_continuity_to_project_config(
        self, manifest: ContinuityManifest, project_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        resolved_config = {**project_config}
        if manifest.preferred_model_profile:
            resolved_config["preferred_model_profile"] = manifest.preferred_model_profile
        if manifest.preferred_provider_profile:
            resolved_config["preferred_provider_profile"] = manifest.preferred_provider_profile
        if manifest.quality_policy:
            resolved_config["quality_policy"] = manifest.quality_policy
        return resolved_config
