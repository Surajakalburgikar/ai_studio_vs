from sqlalchemy.orm import Session
from app.models.generation_job import GenerationJob
from app.prompt_engine.prompt_builder import build_prompts


def create_jobs_for_scene(
    db: Session, scene_id: int, provider: str = "mock", priority: int = 0
) -> list[GenerationJob]:
    """Create generation jobs for all shots in a scene using prompt builder output."""
    # 1. Fetch prompts for the scene (validates scene existence internally)
    prompts = build_prompts(db, scene_id)
    if prompts is None:
        raise ValueError(f"Scene with id {scene_id} not found")

    created_jobs = []
    # 2. Iterate and create a database row per storyboard shot
    for shot in prompts["shots"]:
        job = GenerationJob(
            scene_id=scene_id,
            shot_number=shot["shot_number"],
            provider=provider,
            prompt=shot["positive_prompt"],
            negative_prompt=shot["negative_prompt"],
            filename=shot["image_filename"],
            status="pending",
            priority=priority,
            retry_count=0,
            progress=0,
            drive_file_id=None,
            generation_time=None,
        )
        db.add(job)
        created_jobs.append(job)

    db.commit()
    for job in created_jobs:
        db.refresh(job)

    return created_jobs


def get_next_pending_job(db: Session) -> GenerationJob | None:
    """Return the oldest pending job and transition it to processing."""
    job = (
        db.query(GenerationJob)
        .filter(GenerationJob.status == "pending")
        .order_by(GenerationJob.priority.desc(), GenerationJob.created_at.asc())
        .first()
    )
    if job:
        job.status = "processing"
        db.commit()
        db.refresh(job)
    return job


def update_progress(db: Session, job_id: int, progress: int) -> GenerationJob | None:
    """Update progress percentage of a generation job."""
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if job:
        job.progress = progress
        if job.status == "pending":
            job.status = "processing"
        db.commit()
        db.refresh(job)
    return job


def complete_job(
    db: Session,
    job_id: int,
    drive_file_id: str | None = None,
    generation_time: float | None = None,
) -> GenerationJob | None:
    """Mark a generation job as completed with its metadata."""
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if job:
        job.status = "completed"
        job.progress = 100
        if drive_file_id is not None:
            job.drive_file_id = drive_file_id
        if generation_time is not None:
            job.generation_time = generation_time
        db.commit()
        db.refresh(job)
    return job


def mark_failed(
    db: Session,
    job_id: int,
    error_message: str,
) -> GenerationJob | None:
    """Mark a generation job as failed and save the error message."""
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if job:
        job.status = "failed"
        job.error_message = error_message
        db.commit()
        db.refresh(job)
    return job
