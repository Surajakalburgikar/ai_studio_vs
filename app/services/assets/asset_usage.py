from enum import Enum
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.asset_usage import AssetUsage

class UsagePurpose(str, Enum):
    VIDEO = "VIDEO"
    TRAILER = "TRAILER"
    THUMBNAIL = "THUMBNAIL"
    SHORT = "SHORT"
    FLASHBACK = "FLASHBACK"
    REFERENCE = "REFERENCE"
    TEST = "TEST"

class AssetUsageManager:
    """Manages tracking of asset usages across video assembly and other modules."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def register_usage(
        self,
        asset_id: int,
        project_id: Optional[int],
        episode_id: Optional[int],
        scene_id: Optional[int],
        purpose: str,
        reference_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> AssetUsage:
        """Register a new usage of a specific asset."""
        purpose_str = purpose.value if isinstance(purpose, Enum) else str(purpose)

        usage = AssetUsage(
            asset_id=asset_id,
            project_id=project_id,
            episode_id=episode_id,
            scene_id=scene_id,
            purpose=purpose_str,
            reference_id=reference_id,
            metadata_json=metadata or {}
        )
        self.db.add(usage)
        self.db.commit()
        self.db.refresh(usage)
        return usage

    def remove_usage(self, usage_id: int) -> None:
        """Remove a usage record by its ID."""
        self.db.query(AssetUsage).filter(AssetUsage.usage_id == usage_id).delete(synchronize_session=False)
        self.db.commit()

    def list_usage(self, asset_id: int) -> List[AssetUsage]:
        """List all usages registered for an asset."""
        return self.db.query(AssetUsage).filter(AssetUsage.asset_id == asset_id).all()

    def count_usage(self, asset_id: int) -> int:
        """Count the number of usages registered for an asset."""
        return self.db.query(AssetUsage).filter(AssetUsage.asset_id == asset_id).count()

    def is_safe_to_delete(self, asset_id: int) -> bool:
        """Check if an asset has zero usages, meaning it is safe to delete."""
        return self.count_usage(asset_id) == 0
