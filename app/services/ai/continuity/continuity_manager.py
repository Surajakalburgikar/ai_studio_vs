import os
import json
from typing import Optional, List, Dict, Any
from app.core.config import settings
from .continuity_manifest import ContinuityManifest
from .manifest_revision import RevisionHistory
from .revision_manager import RevisionManager
from .narrative_timeline import NarrativeTimeline


class ContinuityManager:
    """Manages creation, loading, update, and revision history of ContinuityManifest objects.
    
    Sprint 29.1 change: clone_manifest() is DEPRECATED. Use continue_as_new_revision() instead.
    The continuity_key never changes. Each story continuation appends a revision entry.
    """

    def __init__(self, export_path: Optional[str] = None) -> None:
        self.export_path = export_path or settings.CONTINUITY_EXPORT_PATH
        os.makedirs(self.export_path, exist_ok=True)
        self.revision_manager = RevisionManager(self.export_path)

    def _get_file_path(self, continuity_key: str) -> str:
        return os.path.join(self.export_path, f"{continuity_key}.json")

    def _get_timeline_path(self, continuity_key: str) -> str:
        return os.path.join(self.export_path, f"{continuity_key}_timeline.json")

    # ── Manifest CRUD ────────────────────────────────────────────────────────

    def create_new_manifest(
        self,
        continuity_key: str,
        series_title: str = "",
        universe_title: str = "",
    ) -> ContinuityManifest:
        manifest = ContinuityManifest(
            continuity_key=continuity_key,
            series_title=series_title,
            universe_title=universe_title,
        )
        self.save_manifest(manifest)
        return manifest

    def load_manifest(self, continuity_key: str) -> Optional[ContinuityManifest]:
        file_path = self._get_file_path(continuity_key)
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ContinuityManifest.from_dict(data)
        except Exception:
            return None

    def save_manifest(self, manifest: ContinuityManifest) -> None:
        file_path = self._get_file_path(manifest.continuity_key)
        # Load existing raw data so we don't lose revision history stored in the file
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        else:
            raw = {}
        raw.update(manifest.to_dict())
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2, ensure_ascii=False)

    def update_after_completed_step(
        self,
        continuity_key: str,
        project_id: int,
        episode_number: Optional[int] = None,
        scene_number: Optional[int] = None,
        shot_number: Optional[int] = None,
    ) -> None:
        manifest = self.load_manifest(continuity_key)
        if manifest:
            manifest.last_project_id = project_id
            if episode_number is not None:
                manifest.last_episode_number = episode_number
            if scene_number is not None:
                manifest.last_scene_number = scene_number
            if shot_number is not None:
                manifest.last_shot_number = shot_number
            self.save_manifest(manifest)

    def export_manifest(self, continuity_key: str, dest_path: str) -> None:
        manifest = self.load_manifest(continuity_key)
        if not manifest:
            raise ValueError(f"Manifest not found for key: {continuity_key}")
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)

    def import_manifest(self, src_path: str) -> ContinuityManifest:
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Source file not found: {src_path}")
        with open(src_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        manifest = ContinuityManifest.from_dict(data)
        self.save_manifest(manifest)
        return manifest

    # ── Revision History ────────────────────────────────────────────────────

    def add_revision(
        self,
        continuity_key: str,
        reason: str = "",
        author: str = "system",
        summary: str = "",
        project_id: Optional[int] = None,
    ) -> RevisionHistory:
        """Append a revision entry to the manifest WITHOUT changing the continuity_key.
        
        Use this instead of clone_manifest() when continuing a story into a new project.
        """
        manifest = self.load_manifest(continuity_key)
        if not manifest:
            raise ValueError(f"Manifest not found for key: {continuity_key}")
        return self.revision_manager.append_revision(
            manifest, reason=reason, author=author, summary=summary, project_id=project_id
        )

    def list_revisions(self, continuity_key: str) -> List[RevisionHistory]:
        """Return the full revision history for a continuity key, oldest first."""
        return self.revision_manager.list_revisions(continuity_key)

    def get_revision(self, continuity_key: str, revision_number: int) -> Optional[RevisionHistory]:
        """Retrieve a specific revision."""
        return self.revision_manager.get_revision(continuity_key, revision_number)

    def restore_revision(self, continuity_key: str, revision_number: int) -> ContinuityManifest:
        """Restore manifest canonical data to a previous revision state."""
        return self.revision_manager.restore_revision(continuity_key, revision_number)

    def get_current_revision_number(self, continuity_key: str) -> int:
        """Return the current (latest) revision number, or 0 if no revisions exist."""
        revisions = self.list_revisions(continuity_key)
        return revisions[-1].revision_number if revisions else 0

    # ── NarrativeTimeline persistence ───────────────────────────────────────

    def load_timeline(self, continuity_key: str) -> Optional[NarrativeTimeline]:
        path = self._get_timeline_path(continuity_key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return NarrativeTimeline.from_dict(data)
        except Exception:
            return None

    def save_timeline(self, timeline: NarrativeTimeline) -> None:
        path = self._get_timeline_path(timeline.continuity_key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(timeline.to_dict(), f, indent=2, ensure_ascii=False)

    def get_or_create_timeline(self, continuity_key: str) -> NarrativeTimeline:
        timeline = self.load_timeline(continuity_key)
        if not timeline:
            timeline = NarrativeTimeline(continuity_key=continuity_key)
            self.save_timeline(timeline)
        return timeline

    # ── Character State Versioning ──────────────────────────────────────────

    def _get_profile_path(self, continuity_key: str) -> str:
        return os.path.join(self.export_path, f"{continuity_key}_profiles.json")

    def _load_profiles_raw(self, continuity_key: str) -> dict:
        path = self._get_profile_path(continuity_key)
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_profiles_raw(self, continuity_key: str, data: dict) -> None:
        path = self._get_profile_path(continuity_key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def create_character_state(
        self,
        continuity_key: str,
        character_name: str,
        **state_kwargs,
    ) -> "CharacterProfile":
        """Create or reset the versioned character state for a character.

        Returns the new CharacterProfile.
        """
        from .canonical_character import CanonicalCharacter, CharacterState, CharacterProfile
        raw = self._load_profiles_raw(continuity_key)
        if character_name in raw:
            profile = CharacterProfile.from_dict(raw[character_name])
            # If profile already exists, start a fresh state chain (version 1)
        else:
            manifest = self.load_manifest(continuity_key)
            canon_raw = (manifest.canonical_characters or {}).get(character_name, {})
            if canon_raw:
                identity = CanonicalCharacter.from_dict(canon_raw)
            else:
                identity = CanonicalCharacter(
                    character_id=character_name,
                    canonical_name=character_name,
                )
            profile = CharacterProfile(identity=identity)

        new_state = CharacterState(**{
            k: v for k, v in state_kwargs.items() if hasattr(CharacterState, k)
        })
        profile.current_state = new_state
        profile.state_history = []
        raw[character_name] = profile.to_dict()
        self._save_profiles_raw(continuity_key, raw)
        return profile

    def update_character_state(
        self,
        continuity_key: str,
        character_name: str,
        reason: Optional[str] = None,
        **state_kwargs,
    ) -> "CharacterProfile":
        """Append a new version of the character state. Old versions are never erased.

        Returns the updated CharacterProfile.
        """
        from .canonical_character import CanonicalCharacter, CharacterState, CharacterProfile
        raw = self._load_profiles_raw(continuity_key)
        if character_name not in raw:
            return self.create_character_state(continuity_key, character_name, **state_kwargs)
        profile = CharacterProfile.from_dict(raw[character_name])
        profile.update_state(reason=reason, **state_kwargs)
        raw[character_name] = profile.to_dict()
        self._save_profiles_raw(continuity_key, raw)
        return profile

    def list_character_state_versions(
        self,
        continuity_key: str,
        character_name: str,
    ) -> List["CharacterState"]:
        """Return all state versions for a character (history + current), oldest first."""
        from .canonical_character import CharacterProfile, CharacterState
        raw = self._load_profiles_raw(continuity_key)
        if character_name not in raw:
            return []
        profile = CharacterProfile.from_dict(raw[character_name])
        return profile.state_history + [profile.current_state]

    def restore_character_state_version(
        self,
        continuity_key: str,
        character_name: str,
        version: int,
        reason: Optional[str] = None,
    ) -> Optional["CharacterProfile"]:
        """Restore a previous character state version as the new current_state.

        A new version is appended to record the restore. History is never erased.
        Returns the updated CharacterProfile, or None if character/version not found.
        """
        from .canonical_character import CharacterProfile
        raw = self._load_profiles_raw(continuity_key)
        if character_name not in raw:
            return None
        profile = CharacterProfile.from_dict(raw[character_name])
        success = profile.restore_state_version(
            version, reason=reason or f"Restored to state version {version}"
        )
        if not success:
            return None
        raw[character_name] = profile.to_dict()
        self._save_profiles_raw(continuity_key, raw)
        return profile

    # ── Backward-compatibility adapter ─────────────────────────────────────

    def clone_manifest(self, continuity_key: str, new_continuity_key: str) -> ContinuityManifest:
        """DEPRECATED — kept for backward compatibility only.
        
        Sprint 29.1 introduces revision history as the proper mechanism for sequels.
        Callers should migrate to add_revision() + updating new_project.continuity_key
        to the SAME key.  This method still works but logs a deprecation warning.
        """
        import warnings
        warnings.warn(
            "clone_manifest() is deprecated since Sprint 29.1. "
            "Use add_revision() to record story continuations inside the same manifest. "
            "The continuity_key should NOT change across sequels.",
            DeprecationWarning,
            stacklevel=2,
        )
        manifest = self.load_manifest(continuity_key)
        if not manifest:
            raise ValueError(f"Manifest not found for key: {continuity_key}")
        cloned_data = manifest.to_dict()
        cloned_data["continuity_key"] = new_continuity_key
        cloned_data["continuity_version"] = cloned_data.get("continuity_version", 1) + 1
        cloned_manifest = ContinuityManifest.from_dict(cloned_data)
        self.save_manifest(cloned_manifest)
        return cloned_manifest
