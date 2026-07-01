from typing import Optional
from sqlalchemy.orm import Session
from app.models.asset import Asset
from .asset_status import AssetStatus

def get_next_revision_number(db: Session, project_id: Optional[int], scene_id: Optional[int], shot_id: Optional[int]) -> int:
    """Determine the next revision number for a given shot.
    
    If no assets exist for this shot, start at 1. Otherwise, increment from the max revision.
    """
    if project_id is None or scene_id is None or shot_id is None:
        return 1
        
    max_rev = db.query(Asset.revision).filter(
        Asset.project_id == project_id,
        Asset.scene_id == scene_id,
        Asset.shot_id == shot_id
    ).order_by(Asset.revision.desc()).first()
    
    if max_rev:
        return max_rev[0] + 1
    return 1

def mark_revision_canonical(db: Session, asset_id: int) -> Asset:
    """Mark a specific asset revision as canonical/approved.
    
    This updates the target asset status to APPROVED and demotes all other
    revisions of the same shot to ARCHIVED.
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise ValueError(f"Asset with id {asset_id} not found")
        
    # Get all other approved/generated assets for the same shot
    if asset.project_id is not None and asset.scene_id is not None and asset.shot_id is not None:
        other_assets = db.query(Asset).filter(
            Asset.project_id == asset.project_id,
            Asset.scene_id == asset.scene_id,
            Asset.shot_id == asset.shot_id,
            Asset.id != asset_id
        ).all()
        for other in other_assets:
            if other.status in (AssetStatus.APPROVED, AssetStatus.GENERATED):
                other.status = AssetStatus.ARCHIVED
            
    asset.status = AssetStatus.APPROVED
    
    # Update AssetCollection canonical_asset_id (Task 1)
    if asset.collection_id is not None:
        from app.models.asset_collection import AssetCollection
        coll = db.query(AssetCollection).filter(AssetCollection.collection_id == asset.collection_id).first()
        if coll:
            coll.canonical_asset_id = asset.id

    db.commit()
    db.refresh(asset)
    return asset
