import os
import json
import copy
from typing import List, Optional
from .manifest_revision import RevisionHistory
from .continuity_manifest import ContinuityManifest


class RevisionManager:
    """Manages the revision history stored inside a ContinuityManifest file.
    
    Design principle:
      - The continuity_key NEVER changes.
      - The manifest file is the single source of truth.
      - Revisions are appended records *within* the manifest — no files are cloned or duplicated.
    """

    REVISIONS_KEY = "_revision_history"

    def __init__(self, export_path: str) -> None:
        self.export_path = export_path

    def _get_file_path(self, continuity_key: str) -> str:
        return os.path.join(self.export_path, f"{continuity_key}.json")

    def _load_raw(self, continuity_key: str) -> dict:
        path = self._get_file_path(continuity_key)
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_raw(self, continuity_key: str, data: dict) -> None:
        path = self._get_file_path(continuity_key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def append_revision(
        self,
        manifest: ContinuityManifest,
        reason: str = "",
        author: str = "system",
        summary: str = "",
        project_id: Optional[int] = None,
    ) -> RevisionHistory:
        """Snapshot the current manifest state and append it as a new revision entry.
        
        This NEVER clones the manifest into a new file. The continuity_key is unchanged.
        """
        raw = self._load_raw(manifest.continuity_key)
        history = self._parse_history(raw)
        next_rev = (history[-1].revision_number + 1) if history else 1

        revision = RevisionHistory(
            revision_number=next_rev,
            project_id=project_id,
            reason=reason,
            author=author,
            summary=summary,
            character_snapshot=copy.deepcopy(manifest.canonical_characters),
            world_snapshot=copy.deepcopy(manifest.active_world_state),
            timeline_snapshot=copy.deepcopy(manifest.timeline_anchor),
        )

        # Update manifest version counter
        manifest.continuity_version = next_rev

        # Write both the updated manifest and the new revision back to the same file
        raw.update(manifest.to_dict())
        raw.setdefault(self.REVISIONS_KEY, [])
        raw[self.REVISIONS_KEY].append(revision.to_dict())

        self._save_raw(manifest.continuity_key, raw)
        return revision

    def list_revisions(self, continuity_key: str) -> List[RevisionHistory]:
        """Return all revisions for a continuity key, oldest first."""
        raw = self._load_raw(continuity_key)
        return self._parse_history(raw)

    def get_revision(self, continuity_key: str, revision_number: int) -> Optional[RevisionHistory]:
        """Retrieve a specific revision by number."""
        for rev in self.list_revisions(continuity_key):
            if rev.revision_number == revision_number:
                return rev
        return None

    def restore_revision(self, continuity_key: str, revision_number: int) -> ContinuityManifest:
        """Restore the manifest's canonical data to the state captured at a given revision.
        
        A new revision entry is appended to record the restore event itself, so history
        is never lost. The continuity_key remains unchanged.
        """
        raw = self._load_raw(continuity_key)
        history = self._parse_history(raw)

        target = next((r for r in history if r.revision_number == revision_number), None)
        if not target:
            raise ValueError(
                f"Revision {revision_number} not found for continuity key '{continuity_key}'."
            )

        manifest = ContinuityManifest.from_dict(raw)
        # Restore snapshots from the target revision
        manifest.canonical_characters = copy.deepcopy(target.character_snapshot)
        manifest.active_world_state = copy.deepcopy(target.world_snapshot)
        manifest.timeline_anchor = copy.deepcopy(target.timeline_snapshot)

        # Append a restore-event revision
        self.append_revision(
            manifest,
            reason=f"Restored from revision {revision_number}",
            author="system",
            summary=f"Restore to revision {revision_number}",
        )
        return manifest

    # ── helpers ────────────────────────────────────────────────────────────
    def _parse_history(self, raw: dict) -> List[RevisionHistory]:
        return [RevisionHistory.from_dict(r) for r in raw.get(self.REVISIONS_KEY, [])]
