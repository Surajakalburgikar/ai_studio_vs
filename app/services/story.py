from sqlalchemy.orm import Session

from app.models.story import Story
from app.schemas.story import StoryCreate


def create_story(db: Session, project_id: int, payload: StoryCreate) -> Story:
    """Create a new story under the given project."""
    story = Story(
        project_id=project_id,
        title=payload.title,
        genre=payload.genre,
        summary=payload.summary,
        story_text=payload.story_text,
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


def get_stories_by_project(db: Session, project_id: int) -> list[Story]:
    """Return all stories for a project ordered by newest first."""
    return (
        db.query(Story)
        .filter(Story.project_id == project_id)
        .order_by(Story.created_at.desc())
        .all()
    )


def get_story_by_id(db: Session, story_id: int) -> Story | None:
    """Return a single story by its ID, or None if not found."""
    return db.query(Story).filter(Story.id == story_id).first()
