from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.scene import SceneCreate, SceneResponse
from app.schemas.scene_direction import SceneDirectionResponse, SceneDirectionUpdate
from app.services.episode import get_episode_by_id
from app.services.scene import create_scene, get_episode_scenes, get_scene_by_id
from app.services.scene_director import get_scene_direction, save_scene_direction

router = APIRouter(tags=["Scenes"])


@router.post(
    "/episodes/{episode_id}/scenes",
    response_model=SceneResponse,
    status_code=status.HTTP_201_CREATED,
)
def create(episode_id: int, payload: SceneCreate, db: Session = Depends(get_db)):
    """Create a new scene under an episode."""
    episode = get_episode_by_id(db, episode_id)
    if episode is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Episode with id {episode_id} not found",
        )
    return create_scene(db, episode_id, payload)


@router.get("/episodes/{episode_id}/scenes", response_model=list[SceneResponse])
def list_scenes(episode_id: int, db: Session = Depends(get_db)):
    """Return all scenes for an episode."""
    episode = get_episode_by_id(db, episode_id)
    if episode is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Episode with id {episode_id} not found",
        )
    return get_episode_scenes(db, episode_id)


@router.get("/scenes/{scene_id}", response_model=SceneResponse)
def get_scene(scene_id: int, db: Session = Depends(get_db)):
    """Return a single scene by ID."""
    scene = get_scene_by_id(db, scene_id)
    if scene is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene with id {scene_id} not found",
        )
    return scene


@router.get("/scenes/{scene_id}/direction", response_model=SceneDirectionResponse)
def get_direction(scene_id: int, db: Session = Depends(get_db)):
    """Calculate and return the complete directing plan for a scene."""
    plan = get_scene_direction(db, scene_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene with id {scene_id} not found",
        )
    return plan


@router.put("/scenes/{scene_id}/direction", response_model=SceneDirectionResponse)
def update_direction(
    scene_id: int,
    payload: SceneDirectionUpdate,
    db: Session = Depends(get_db)
):
    """Overwrite custom timeline events for a scene's directing plan."""
    scene = get_scene_by_id(db, scene_id)
    if scene is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene with id {scene_id} not found",
        )
    
    save_scene_direction(db, scene_id, payload.timeline_events)
    return get_scene_direction(db, scene_id)
