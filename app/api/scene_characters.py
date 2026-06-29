from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.character import CharacterResponse
from app.schemas.scene import SceneResponse
from app.schemas.scene_character import SceneCharacterResponse
from app.services.scene_character import (
    assign_character_to_scene,
    get_character_scenes,
    get_scene_characters,
)

router = APIRouter(tags=["Scene Character Mapping"])


@router.post(
    "/scenes/{scene_id}/characters/{character_id}",
    response_model=SceneCharacterResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_character(scene_id: int, character_id: int, db: Session = Depends(get_db)):
    """Assign a character to a scene."""
    result = assign_character_to_scene(db, scene_id, character_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scene or Character not found",
        )
    return result


@router.get("/scenes/{scene_id}/characters", response_model=list[CharacterResponse])
def get_scene_chars(scene_id: int, db: Session = Depends(get_db)):
    """Retrieve all characters assigned to a scene."""
    characters = get_scene_characters(db, scene_id)
    if characters is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene with id {scene_id} not found",
        )
    return characters


@router.get("/characters/{character_id}/scenes", response_model=list[SceneResponse])
def get_char_scenes(character_id: int, db: Session = Depends(get_db)):
    """Retrieve all scenes a character is assigned to."""
    scenes = get_character_scenes(db, character_id)
    if scenes is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )
    return scenes
