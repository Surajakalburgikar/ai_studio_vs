from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.prompt import PromptResponse
from app.prompt_engine.prompt_builder import build_prompts

router = APIRouter(tags=["Prompt Engine"])


@router.get(
    "/scenes/{scene_id}/prompts",
    response_model=PromptResponse,
    status_code=status.HTTP_200_OK,
)
def get_prompts(scene_id: int, db: Session = Depends(get_db)):
    """Dynamically generate production-ready prompts for all scene shots."""
    prompts = build_prompts(db, scene_id)
    if prompts is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene with id {scene_id} not found",
        )
    return prompts
