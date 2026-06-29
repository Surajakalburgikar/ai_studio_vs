from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.project import ProjectCreate, ProjectResponse
from app.schemas.production_plan import ProductionPlanResponse, ProductionPlanUpdate
from app.services.project import create_project, get_all_projects, get_project_by_id
from app.services.production_plan import get_production_plan_by_project_id, save_production_plan

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create(payload: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project."""
    return create_project(db, payload)


@router.get("/", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    """Return all projects."""
    return get_all_projects(db)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Return a single project by ID."""
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found",
        )
    return project


@router.get("/{project_id}/production-plan", response_model=ProductionPlanResponse)
def get_production_plan(project_id: int, db: Session = Depends(get_db)):
    """Calculate and return the production plan for a project."""
    plan = get_production_plan_by_project_id(db, project_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found",
        )
    return plan


@router.put("/{project_id}/production-plan", response_model=ProductionPlanResponse)
def update_production_plan(
    project_id: int,
    payload: ProductionPlanUpdate,
    db: Session = Depends(get_db)
):
    """Save or update custom profiles for a project's production plan."""
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found",
        )
    
    save_production_plan(
        db,
        project_id,
        payload.animation_profile,
        payload.production_profile,
        payload.quality_profile
    )
    
    return get_production_plan_by_project_id(db, project_id)
