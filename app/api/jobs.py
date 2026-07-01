from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.generation_job import (
    GenerationJobComplete,
    GenerationJobCreate,
    GenerationJobFailed,
    GenerationJobProgress,
    GenerationJobResponse,
)
from app.services import generation_job as job_service
from app.services.scene import get_scene_by_id

router = APIRouter(prefix="/jobs", tags=["Generation Jobs"])


@router.post(
    "",
    response_model=list[GenerationJobResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_jobs(payload: GenerationJobCreate, db: Session = Depends(get_db)):
    """Create generation jobs for all storyboard shots in a scene."""
    scene = get_scene_by_id(db, payload.scene_id)
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene with id {payload.scene_id} not found",
        )

    try:
        jobs = job_service.create_jobs_for_scene(
            db=db,
            scene_id=payload.scene_id,
            provider=payload.provider or "mock",
            priority=payload.priority or 0,
        )
        return jobs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create jobs: {str(e)}",
        )


@router.get(
    "/next",
    response_model=GenerationJobResponse,
    status_code=status.HTTP_200_OK,
)
def get_next_job(db: Session = Depends(get_db)):
    """Return the oldest pending job and mark it as processing."""
    job = job_service.get_next_pending_job(db)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending jobs found",
        )
    return job


@router.patch(
    "/{id}/progress",
    response_model=GenerationJobResponse,
    status_code=status.HTTP_200_OK,
)
def update_job_progress(
    id: int,
    payload: GenerationJobProgress,
    db: Session = Depends(get_db),
):
    """Update progress of a generation job."""
    job = job_service.update_progress(db, job_id=id, progress=payload.progress)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation job with id {id} not found",
        )
    return job


@router.post(
    "/{id}/complete",
    response_model=GenerationJobResponse,
    status_code=status.HTTP_200_OK,
)
def complete_job_endpoint(
    id: int,
    payload: GenerationJobComplete,
    db: Session = Depends(get_db),
):
    """Mark a generation job as completed."""
    job = job_service.complete_job(
        db,
        job_id=id,
        drive_file_id=payload.drive_file_id,
        generation_time=payload.generation_time,
        provider=payload.provider,
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation job with id {id} not found",
        )
    return job


@router.post(
    "/{job_id}/failed",
    response_model=GenerationJobResponse,
    status_code=status.HTTP_200_OK,
)
def fail_job_endpoint(
    job_id: int,
    payload: GenerationJobFailed,
    db: Session = Depends(get_db),
):
    """Mark a generation job as failed."""
    job = job_service.mark_failed(
        db,
        job_id=job_id,
        error_message=payload.error_message,
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation job with id {job_id} not found",
        )
    return job
