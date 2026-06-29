from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.story import StoryCreate, StoryResponse
from app.services.project import get_project_by_id
from app.services.story import create_story, get_stories_by_project, get_story_by_id

router = APIRouter(tags=["Stories"])


@router.post(
    "/projects/{project_id}/stories",
    response_model=StoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create(project_id: int, payload: StoryCreate, db: Session = Depends(get_db)):
    """Create a new story under a project."""
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found",
        )
    return create_story(db, project_id, payload)


@router.get("/projects/{project_id}/stories", response_model=list[StoryResponse])
def list_stories(project_id: int, db: Session = Depends(get_db)):
    """Return all stories for a project."""
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found",
        )
    return get_stories_by_project(db, project_id)


@router.get("/stories/{story_id}", response_model=StoryResponse)
def get_story(story_id: int, db: Session = Depends(get_db)):
    """Return a single story by ID."""
    story = get_story_by_id(db, story_id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story with id {story_id} not found",
        )
    return story
