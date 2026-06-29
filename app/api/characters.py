from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.character import CharacterCreate, CharacterResponse
from app.services.character import create_character, get_character, get_story_characters
from app.services.story import get_story_by_id

router = APIRouter(tags=["Characters"])


@router.post(
    "/stories/{story_id}/characters",
    response_model=CharacterResponse,
    status_code=status.HTTP_201_CREATED,
)
def create(story_id: int, payload: CharacterCreate, db: Session = Depends(get_db)):
    """Create a new character under a story."""
    story = get_story_by_id(db, story_id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story with id {story_id} not found",
        )
    return create_character(db, story_id, payload)


@router.get("/stories/{story_id}/characters", response_model=list[CharacterResponse])
def list_characters(story_id: int, db: Session = Depends(get_db)):
    """Return all characters for a story."""
    story = get_story_by_id(db, story_id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story with id {story_id} not found",
        )
    return get_story_characters(db, story_id)


@router.get("/characters/{character_id}", response_model=CharacterResponse)
def get_character_endpoint(character_id: int, db: Session = Depends(get_db)):
    """Return a single character by ID."""
    character = get_character(db, character_id)
    if character is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )
    return character
