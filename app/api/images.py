from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.providers.image import image_provider_manager, ImageResult
from app.prompt_engine.prompt_builder import build_prompts

router = APIRouter(tags=["Image Generation"])


@router.get(
    "/scenes/{scene_id}/generate-image",
    response_model=list[ImageResult],
    status_code=status.HTTP_200_OK,
)
def generate_images_for_scene(scene_id: int, db: Session = Depends(get_db)):
    """Generate mock images for all storyboard shots in a scene."""
    prompts = build_prompts(db, scene_id)
    if prompts is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene with id {scene_id} not found",
        )

    results = []
    for shot in prompts["shots"]:
        result = image_provider_manager.generate(
            prompt=shot["positive_prompt"],
            filename=shot["image_filename"],
        )
        results.append(result)

    return results
