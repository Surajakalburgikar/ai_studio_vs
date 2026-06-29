from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.episode import EpisodeCreate, EpisodeResponse
from app.services.episode import create_episode, get_episode_by_id, get_story_episodes
from app.services.story import get_story_by_id

router = APIRouter(tags=["Episodes"])


@router.post(
    "/stories/{story_id}/episodes",
    response_model=EpisodeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create(story_id: int, payload: EpisodeCreate, db: Session = Depends(get_db)):
    """Create a new episode under a story."""
    story = get_story_by_id(db, story_id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story with id {story_id} not found",
        )
    return create_episode(db, story_id, payload)


@router.get("/stories/{story_id}/episodes", response_model=list[EpisodeResponse])
def list_episodes(story_id: int, db: Session = Depends(get_db)):
    """Return all episodes for a story."""
    story = get_story_by_id(db, story_id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story with id {story_id} not found",
        )
    return get_story_episodes(db, story_id)


@router.get("/episodes/{episode_id}", response_model=EpisodeResponse)
def get_episode(episode_id: int, db: Session = Depends(get_db)):
    """Return a single episode by ID."""
    episode = get_episode_by_id(db, episode_id)
    if episode is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Episode with id {episode_id} not found",
        )
    return episode
