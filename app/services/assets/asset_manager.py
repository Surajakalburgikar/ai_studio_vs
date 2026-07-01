from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.generation_job import GenerationJob
from app.models.asset import Asset
from .asset_registry import AssetRegistry
from .asset_repository import AssetRepository

class AssetManager:
    """High-level coordinator interfacing with repository searches and registration pipelines."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.registry = AssetRegistry(db)
        self.repository = AssetRepository(db)

    def register_completed_job(self, job: GenerationJob) -> Asset:
        """Invoked upon job completion to add a new asset entry to the catalog."""
        return self.registry.register_asset(job)

    def approve_asset(self, asset_id: int) -> Asset:
        """Mark an asset approved."""
        return self.registry.approve_asset(asset_id)

    def reject_asset(self, asset_id: int) -> Asset:
        """Mark an asset rejected."""
        return self.registry.reject_asset(asset_id)

    def archive_asset(self, asset_id: int) -> Asset:
        """Mark an asset archived."""
        return self.registry.archive_asset(asset_id)

    def get_asset(self, asset_id: int) -> Optional[Asset]:
        """Fetch asset by ID."""
        return self.repository.get_by_id(asset_id)

    def list_assets(self, **filters) -> List[Asset]:
        """Query and filter list of assets."""
        return self.repository.find_assets(**filters)

    def safe_delete(self, asset_id: int, force: bool = False) -> None:
        """Delete an asset only if it is not in use, or if force is True."""
        asset = self.get_asset(asset_id)
        if not asset:
            raise ValueError(f"Asset with id {asset_id} not found")

        from .asset_usage import AssetUsageManager
        usage_mgr = AssetUsageManager(self.db)
        if not force and not usage_mgr.is_safe_to_delete(asset_id):
            usage_count = usage_mgr.count_usage(asset_id)
            raise ValueError(
                f"Asset {asset_id} cannot be safely deleted because it has {usage_count} active usage(s)."
            )

        self.db.delete(asset)
        self.db.commit()
