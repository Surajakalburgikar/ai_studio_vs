from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.storyboard import StoryboardResponse
from app.storyboard.storyboard_generator import generate_storyboard

router = APIRouter(tags=["Storyboard"])


@router.get(
    "/scenes/{scene_id}/storyboard",
    response_model=StoryboardResponse,
    status_code=status.HTTP_200_OK,
)
def get_storyboard(scene_id: int, db: Session = Depends(get_db)):
    """Dynamically generate storyboard for a scene."""
    storyboard = generate_storyboard(db, scene_id)
    if storyboard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene with id {scene_id} not found",
        )
    return storyboard
