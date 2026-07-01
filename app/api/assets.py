from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.session import get_db
from pydantic import BaseModel
from app.schemas.asset import AssetResponse, AssetCollectionResponse, AssetUsageResponse
from app.services.assets.asset_manager import AssetManager

router = APIRouter(prefix="/assets", tags=["Asset Registry"])

@router.get("", response_model=List[AssetResponse])
def list_assets(
    continuity_key: Optional[str] = None,
    project_id: Optional[int] = None,
    episode_id: Optional[int] = None,
    scene_id: Optional[int] = None,
    shot_id: Optional[int] = None,
    generation_job_id: Optional[int] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[str] = None,
    revision: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List assets, optionally filtered by continuity, project, scene, shot, status, revision."""
    manager = AssetManager(db)
    return manager.list_assets(
        continuity_key=continuity_key,
        project_id=project_id,
        episode_id=episode_id,
        scene_id=scene_id,
        shot_id=shot_id,
        generation_job_id=generation_job_id,
        provider=provider,
        model=model,
        status=status,
        revision=revision
    )

@router.get("/{id}", response_model=AssetResponse)
def get_asset_by_id(id: int, db: Session = Depends(get_db)):
    """Retrieve asset by its ID."""
    manager = AssetManager(db)
    asset = manager.get_asset(id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with id {id} not found"
        )
    return asset

@router.get("/scene/{scene_id}", response_model=List[AssetResponse])
def get_assets_by_scene(scene_id: int, db: Session = Depends(get_db)):
    """Get all assets associated with a specific scene."""
    manager = AssetManager(db)
    return manager.list_assets(scene_id=scene_id)

@router.get("/shot/{shot_id}", response_model=List[AssetResponse])
def get_assets_by_shot(shot_id: int, db: Session = Depends(get_db)):
    """Get all assets associated with a specific shot ID (shot number)."""
    manager = AssetManager(db)
    return manager.list_assets(shot_id=shot_id)

@router.get("/project/{project_id}", response_model=List[AssetResponse])
def get_assets_by_project(project_id: int, db: Session = Depends(get_db)):
    """Get all assets associated with a project."""
    manager = AssetManager(db)
    return manager.list_assets(project_id=project_id)

@router.get("/continuity/{continuity_key}", response_model=List[AssetResponse])
def get_assets_by_continuity(continuity_key: str, db: Session = Depends(get_db)):
    """Get all assets associated with a continuity key."""
    manager = AssetManager(db)
    return manager.list_assets(continuity_key=continuity_key)

@router.post("/{id}/approve", response_model=AssetResponse)
def approve_asset_revision(id: int, db: Session = Depends(get_db)):
    """Mark an asset revision as APPROVED and canonical for that shot, archiving others."""
    manager = AssetManager(db)
    try:
        return manager.approve_asset(id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.post("/{id}/reject", response_model=AssetResponse)
def reject_asset_revision(id: int, db: Session = Depends(get_db)):
    """Mark an asset revision as REJECTED."""
    manager = AssetManager(db)
    try:
        return manager.reject_asset(id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.post("/{id}/archive", response_model=AssetResponse)
def archive_asset_revision(id: int, db: Session = Depends(get_db)):
    """Mark an asset revision as ARCHIVED."""
    manager = AssetManager(db)
    try:
        return manager.archive_asset(id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.post("/{id}/canonical", response_model=AssetResponse)
def make_asset_canonical(id: int, db: Session = Depends(get_db)):
    """Mark an asset revision as canonical (Approved), archiving others for the same shot."""
    manager = AssetManager(db)
    try:
        return manager.approve_asset(id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.get("/{id}/history", response_model=List[AssetResponse])
def get_asset_revision_history(id: int, db: Session = Depends(get_db)):
    """Get the full revision history for the shot associated with this asset."""
    manager = AssetManager(db)
    asset = manager.get_asset(id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with id {id} not found"
        )
    return manager.repository.revision_history(
        project_id=asset.project_id,
        scene_id=asset.scene_id,
        shot_id=asset.shot_id
    )


class TagsRequest(BaseModel):
    tags: List[str]


class UsageRequest(BaseModel):
    project_id: Optional[int] = None
    episode_id: Optional[int] = None
    scene_id: Optional[int] = None
    purpose: str
    reference_id: Optional[str] = None
    metadata: Optional[dict] = None


@router.get("/collection/{collection_id}", response_model=AssetCollectionResponse)
def get_collection(collection_id: int, db: Session = Depends(get_db)):
    """Retrieve asset collection details by its ID."""
    from app.services.assets.asset_collection import AssetCollectionRepository
    repo = AssetCollectionRepository(db)
    coll = repo.get_collection(collection_id)
    if not coll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset collection {collection_id} not found"
        )
    return coll


@router.get("/tag/{tag}", response_model=List[AssetResponse])
def get_assets_by_tag(tag: str, db: Session = Depends(get_db)):
    """Find all assets associated with the given tag case-insensitively."""
    from app.services.assets.asset_tags import AssetTagManager
    mgr = AssetTagManager(db)
    return mgr.search_by_tag(tag)


@router.get("/{asset_id}/usage", response_model=List[AssetUsageResponse])
def get_asset_usages(asset_id: int, db: Session = Depends(get_db)):
    """List all usages registered for an asset."""
    from app.services.assets.asset_usage import AssetUsageManager
    mgr = AssetUsageManager(db)
    return mgr.list_usage(asset_id)


@router.post("/{asset_id}/tags")
def add_asset_tags(asset_id: int, request: TagsRequest, db: Session = Depends(get_db)):
    """Add one or more tags to an asset."""
    from app.services.assets.asset_tags import AssetTagManager
    mgr = AssetTagManager(db)
    for tag in request.tags:
        mgr.add_tag(asset_id, tag)
    return {"status": "success", "tags": mgr.list_tags(asset_id)}


@router.delete("/{asset_id}/tags/{tag}")
def remove_asset_tag(asset_id: int, tag: str, db: Session = Depends(get_db)):
    """Remove a specific tag from an asset case-insensitively."""
    from app.services.assets.asset_tags import AssetTagManager
    mgr = AssetTagManager(db)
    mgr.remove_tag(asset_id, tag)
    return {"status": "success"}


@router.post("/{asset_id}/usage", response_model=AssetUsageResponse)
def register_asset_usage(asset_id: int, request: UsageRequest, db: Session = Depends(get_db)):
    """Register a new usage for an asset."""
    from app.services.assets.asset_usage import AssetUsageManager
    mgr = AssetUsageManager(db)
    try:
        return mgr.register_usage(
            asset_id=asset_id,
            project_id=request.project_id,
            episode_id=request.episode_id,
            scene_id=request.scene_id,
            purpose=request.purpose,
            reference_id=request.reference_id,
            metadata=request.metadata
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{asset_id}/usage/{usage_id}")
def remove_asset_usage(asset_id: int, usage_id: int, db: Session = Depends(get_db)):
    """Remove a registered usage record."""
    from app.services.assets.asset_usage import AssetUsageManager
    mgr = AssetUsageManager(db)
    mgr.remove_usage(usage_id)
    return {"status": "success"}


@router.post("/{asset_id}/safe-delete")
def safe_delete_asset(asset_id: int, force: bool = False, db: Session = Depends(get_db)):
    """Delete an asset only if it has no active usages, or if force is True."""
    manager = AssetManager(db)
    try:
        manager.safe_delete(asset_id, force=force)
        return {"status": "success", "message": f"Asset {asset_id} deleted successfully."}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
