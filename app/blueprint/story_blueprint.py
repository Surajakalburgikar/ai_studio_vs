from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.story import Story
from app.models.episode import Episode
from app.models.scene import Scene


class BlueprintResponse(BaseModel):
    """Schema for the story blueprint response."""

    story_id: int
    story_title: str
    total_episodes: int
    total_scenes: int
    total_estimated_duration_seconds: float
    total_estimated_duration_minutes: float
    average_scene_duration: float
    ordered_episode_numbers: list[int]
    ordered_scene_numbers_by_episode: dict[int, list[int]]

    model_config = {"from_attributes": True}


router = APIRouter(tags=["Blueprints"])


@router.get("/stories/{story_id}/blueprint", response_model=BlueprintResponse)
def get_story_blueprint(story_id: int, db: Session = Depends(get_db)):
    """Generate and return a structured blueprint for a given story."""
    # 1. Verify Story exists
    story = db.query(Story).filter(Story.id == story_id).first()
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story with id {story_id} not found",
        )

    # 2. Load its episodes ordered by episode_number ascending
    episodes = (
        db.query(Episode)
        .filter(Episode.story_id == story_id)
        .order_by(Episode.episode_number.asc())
        .all()
    )

    total_episodes = len(episodes)
    ordered_episode_numbers = [ep.episode_number for ep in episodes]

    total_scenes = 0
    total_estimated_duration_seconds = 0.0
    ordered_scene_numbers_by_episode = {}

    for ep in episodes:
        # Load scenes ordered by scene_number ascending
        scenes = (
            db.query(Scene)
            .filter(Scene.episode_id == ep.id)
            .order_by(Scene.scene_number.asc())
            .all()
        )

        scene_numbers = []
        for sc in scenes:
            scene_numbers.append(sc.scene_number)
            total_scenes += 1
            if sc.duration_seconds is not None:
                total_estimated_duration_seconds += sc.duration_seconds

        ordered_scene_numbers_by_episode[ep.episode_number] = scene_numbers

    total_estimated_duration_minutes = total_estimated_duration_seconds / 60.0
    average_scene_duration = (
        total_estimated_duration_seconds / total_scenes if total_scenes > 0 else 0.0
    )

    return BlueprintResponse(
        story_id=story.id,
        story_title=story.title,
        total_episodes=total_episodes,
        total_scenes=total_scenes,
        total_estimated_duration_seconds=total_estimated_duration_seconds,
        total_estimated_duration_minutes=total_estimated_duration_minutes,
        average_scene_duration=average_scene_duration,
        ordered_episode_numbers=ordered_episode_numbers,
        ordered_scene_numbers_by_episode=ordered_scene_numbers_by_episode,
    )
