from sqlalchemy.orm import Session

from app.models.scene import Scene
from app.schemas.scene import SceneCreate


def create_scene(db: Session, episode_id: int, payload: SceneCreate) -> Scene:
    """Create a new scene under the given episode."""
    scene = Scene(
        episode_id=episode_id,
        scene_number=payload.scene_number,
        title=payload.title,
        narration=payload.narration,
        camera_notes=payload.camera_notes,
        duration_seconds=payload.duration_seconds,
    )
    db.add(scene)
    db.commit()
    db.refresh(scene)
    return scene


def get_episode_scenes(db: Session, episode_id: int) -> list[Scene]:
    """Return all scenes for an episode ordered by scene number."""
    return (
        db.query(Scene)
        .filter(Scene.episode_id == episode_id)
        .order_by(Scene.scene_number.asc())
        .all()
    )


def get_scene_by_id(db: Session, scene_id: int) -> Scene | None:
    """Return a single scene by its ID, or None if not found."""
    return db.query(Scene).filter(Scene.id == scene_id).first()
