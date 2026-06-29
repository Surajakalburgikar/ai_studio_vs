from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.assets import AssetManager, AssetResponse

router = APIRouter(tags=["Asset Manager"])


@router.get(
    "/scenes/{scene_id}/assets",
    response_model=AssetResponse,
    status_code=status.HTTP_200_OK,
)
def get_scene_assets(scene_id: int, db: Session = Depends(get_db)):
    """Retrieve directory layout, existing files, and manifest for a scene."""
    try:
        manager = AssetManager(db, scene_id)
        return manager.get_assets_info()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
