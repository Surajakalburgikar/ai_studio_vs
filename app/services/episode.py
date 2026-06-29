from sqlalchemy.orm import Session

from app.models.episode import Episode
from app.schemas.episode import EpisodeCreate


def create_episode(db: Session, story_id: int, payload: EpisodeCreate) -> Episode:
    """Create a new episode under the given story."""
    episode = Episode(
        story_id=story_id,
        episode_number=payload.episode_number,
        title=payload.title,
        summary=payload.summary,
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return episode


def get_story_episodes(db: Session, story_id: int) -> list[Episode]:
    """Return all episodes for a story ordered by episode number."""
    return (
        db.query(Episode)
        .filter(Episode.story_id == story_id)
        .order_by(Episode.episode_number.asc())
        .all()
    )


def get_episode_by_id(db: Session, episode_id: int) -> Episode | None:
    """Return a single episode by its ID, or None if not found."""
    return db.query(Episode).filter(Episode.id == episode_id).first()
