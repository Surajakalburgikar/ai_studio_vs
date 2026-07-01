from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.asset import Asset
from app.models.asset_collection import AssetCollection
from .asset_status import AssetStatus

class AssetCollectionRepository:
    """Handles lookups, creation, and canonical management of asset collections."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_collection(
        self,
        project_id: Optional[int],
        episode_id: Optional[int],
        scene_id: Optional[int],
        shot_number: Optional[int],
        continuity_key: Optional[str],
        collection_name: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> AssetCollection:
        """Create a new AssetCollection row."""
        if not collection_name:
            collection_name = f"Collection for Project {project_id}, Scene {scene_id}, Shot {shot_number}"

        coll = AssetCollection(
            project_id=project_id,
            episode_id=episode_id,
            scene_id=scene_id,
            shot_number=shot_number,
            continuity_key=continuity_key,
            collection_name=collection_name,
            metadata_json=metadata or {}
        )
        self.db.add(coll)
        self.db.commit()
        self.db.refresh(coll)
        return coll

    def get_collection(self, collection_id: int) -> Optional[AssetCollection]:
        """Fetch asset collection by its ID."""
        return self.db.query(AssetCollection).filter(AssetCollection.collection_id == collection_id).first()

    def list_assets(self, collection_id: int) -> List[Asset]:
        """List all assets belonging to the collection, ordered by revision ascending."""
        return self.db.query(Asset).filter(Asset.collection_id == collection_id).order_by(Asset.revision.asc()).all()

    def latest_revision(self, collection_id: int) -> Optional[Asset]:
        """Get the latest revision asset in the collection."""
        return self.db.query(Asset).filter(Asset.collection_id == collection_id).order_by(Asset.revision.desc()).first()

    def approved_asset(self, collection_id: int) -> Optional[Asset]:
        """Get the approved (canonical) asset in the collection."""
        return self.db.query(Asset).filter(
            Asset.collection_id == collection_id,
            Asset.status == AssetStatus.APPROVED
        ).first()

    def set_canonical_asset(self, collection_id: int, asset_id: int) -> Optional[AssetCollection]:
        """Set the canonical asset ID for the collection."""
        coll = self.get_collection(collection_id)
        if coll:
            coll.canonical_asset_id = asset_id
            self.db.commit()
            self.db.refresh(coll)
        return coll
