from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
from datetime import datetime, timezone


@dataclass
class RevisionHistory:
    """A single snapshot/revision entry appended to a ContinuityManifest's revision log.
    
    The continuity_key NEVER changes between revisions. The manifest file is the single source
    of truth; revisions are appended records inside it, not separate files.
    """
    revision_number: int
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    project_id: Optional[int] = None
    reason: str = ""
    author: str = "system"
    summary: str = ""
    # Snapshots of the universe state at the time of this revision
    timeline_snapshot: Dict[str, Any] = field(default_factory=dict)
    character_snapshot: Dict[str, Any] = field(default_factory=dict)
    world_snapshot: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RevisionHistory":
        return cls(
            revision_number=data["revision_number"],
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            project_id=data.get("project_id"),
            reason=data.get("reason", ""),
            author=data.get("author", "system"),
            summary=data.get("summary", ""),
            timeline_snapshot=data.get("timeline_snapshot", {}),
            character_snapshot=data.get("character_snapshot", {}),
            world_snapshot=data.get("world_snapshot", {}),
            metadata=data.get("metadata", {}),
        )
