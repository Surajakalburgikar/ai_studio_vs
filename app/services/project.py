from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.project import ProjectCreate


def create_project(db: Session, payload: ProjectCreate) -> Project:
    """Create a new project and persist it to the database."""
    project = Project(
        title=payload.title,
        description=payload.description,
        video_type=payload.video_type,
        target_duration_seconds=payload.target_duration_seconds,
        aspect_ratio=payload.aspect_ratio,
        language=payload.language,
        art_style=payload.art_style,
        narration_style=payload.narration_style,
        subtitle_language=payload.subtitle_language,
        voice_gender=payload.voice_gender,
        preferred_story_model=payload.preferred_story_model,
    )

    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_all_projects(db: Session) -> list[Project]:
    """Return all projects ordered by newest first."""
    return db.query(Project).order_by(Project.created_at.desc()).all()


def get_project_by_id(db: Session, project_id: int) -> Project | None:
    """Return a single project by its ID, or None if not found."""
    return db.query(Project).filter(Project.id == project_id).first()
