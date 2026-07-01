from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
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


# Helper functions for generation
def process_project_jobs(db: Session, project_id: int):
    import sys
    import os
    if "c:/Projects/AI_STUDIO_WORKER" not in sys.path:
        sys.path.append("c:/Projects/AI_STUDIO_WORKER")
    
    from worker.models.job import GenerationJob as WorkerJob
    from worker.execution.executor import Executor
    
    executor = Executor()
    
    while True:
        from app.models.generation_job import GenerationJob as DBJob
        from app.models.scene import Scene
        from app.models.episode import Episode
        from app.models.story import Story
        
        db_job = (
            db.query(DBJob)
            .join(Scene)
            .join(Episode)
            .join(Story)
            .filter(Story.project_id == project_id)
            .filter(DBJob.status == "pending")
            .order_by(DBJob.priority.desc(), DBJob.id.asc())
            .first()
        )
        if not db_job:
            break
            
        db_job.status = "processing"
        db_job.progress = 10
        db.commit()
        db.refresh(db_job)
        
        job_dict = {
            "id": db_job.id,
            "scene_id": db_job.scene_id,
            "shot_number": db_job.shot_number,
            "provider": db_job.provider,
            "prompt": db_job.prompt,
            "negative_prompt": db_job.negative_prompt,
            "filename": db_job.filename,
            "status": db_job.status,
            "priority": db_job.priority,
            "retry_count": db_job.retry_count,
            "progress": db_job.progress,
            "project_id": db_job.project_id,
            "scene_number": db_job.scene_number,
        }
        worker_job = WorkerJob.from_dict(job_dict)
        
        try:
            result = executor.execute(worker_job)
            
            if result.success:
                from app.services.generation_job import complete_job
                complete_job(
                    db=db,
                    job_id=db_job.id,
                    drive_file_id=result.image_path,
                    generation_time=result.generation_time,
                    provider=result.provider
                )
            else:
                raise Exception(result.message)
        except Exception as e:
            from app.services.generation_job import mark_failed
            mark_failed(db=db, job_id=db_job.id, error_message=str(e))


def run_project_generation_in_background(project_id: int):
    from app.database.session import SessionLocal
    from app.services.ai.pipeline.project_pipeline import ProjectPipeline
    from app.models.project import Project
    
    db = SessionLocal()
    try:
        pipeline = ProjectPipeline(db)
        pipeline.generate_project(project_id)
        process_project_jobs(db, project_id)
    except Exception as e:
        print(f"Error in background generation for project {project_id}: {e}")
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = "failed"
            db.commit()
    finally:
        db.close()


@router.post("/{project_id}/generate", status_code=status.HTTP_202_ACCEPTED)
def generate_project(
    project_id: int,
    async_mode: bool = Query(True),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """Generate every image for every shot in every scene of a project automatically."""
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found",
        )
    
    project.status = "processing"
    db.commit()
    
    if async_mode:
        if background_tasks is None:
            raise HTTPException(status_code=500, detail="BackgroundTasks dependency failed")
        background_tasks.add_task(run_project_generation_in_background, project_id)
        return {
            "message": "Project generation started in the background",
            "project_id": project_id,
            "status": "processing"
        }
    else:
        # Sync mode - block until complete
        from app.services.ai.pipeline.project_pipeline import ProjectPipeline
        try:
            pipeline = ProjectPipeline(db)
            pipeline.generate_project(project_id)
            process_project_jobs(db, project_id)
            
            # Fetch final summary from database
            from app.models.generation_job import GenerationJob
            from app.models.scene import Scene
            from app.models.episode import Episode
            from app.models.story import Story
            
            jobs = (
                db.query(GenerationJob)
                .join(Scene)
                .join(Episode)
                .join(Story)
                .filter(Story.project_id == project_id)
                .all()
            )
            
            total_shots = len(jobs)
            completed_shots = sum(1 for j in jobs if j.status == "completed")
            failed_shots = sum(1 for j in jobs if j.status == "failed")
            
            return {
                "message": "Project generation completed",
                "project_id": project_id,
                "status": project.status,
                "total_shots": total_shots,
                "completed_shots": completed_shots,
                "failed_shots": failed_shots,
            }
        except Exception as e:
            project.status = "failed"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Project generation failed: {str(e)}"
            )


@router.get("/{project_id}/generation-status", response_model=dict)
def get_generation_status(project_id: int, db: Session = Depends(get_db)):
    """Return the progress status and metrics of a project generation run."""
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found",
        )
        
    from app.models.scene import Scene
    from app.models.episode import Episode
    from app.models.story import Story
    from app.models.generation_job import GenerationJob
    
    # Get all scenes
    scenes = (
        db.query(Scene)
        .join(Episode)
        .join(Story)
        .filter(Story.project_id == project_id)
        .all()
    )
    total_scenes = len(scenes)
    completed_scenes = sum(1 for s in scenes if s.status == "completed")
    
    # Get all jobs
    jobs = (
        db.query(GenerationJob)
        .join(Scene)
        .join(Episode)
        .join(Story)
        .filter(Story.project_id == project_id)
        .all()
    )
    
    total_shots = len(jobs)
    completed_shots = sum(1 for j in jobs if j.status == "completed")
    failed_shots = sum(1 for j in jobs if j.status == "failed")
    
    # Determine current scene and shot
    current_scene = None
    current_shot = None
    
    # Look for active/processing job first
    active_job = next((j for j in jobs if j.status == "processing"), None)
    if not active_job:
        # Fallback to first pending job
        active_job = next((j for j in jobs if j.status == "pending"), None)
    
    if active_job:
        current_scene = active_job.scene_number
        current_shot = active_job.shot_number
    elif jobs:
        # If all done, default to last shot
        last_job = max(jobs, key=lambda j: (j.scene_number or 0, j.shot_number))
        current_scene = last_job.scene_number
        current_shot = last_job.shot_number
        
    # Provider metrics
    provider_metrics = {}
    for job in jobs:
        if job.status == "completed" and job.provider:
            # Format provider name to get the base (e.g. "mock" or "flux")
            prov_name = job.provider.split()[0].lower()
            if prov_name not in provider_metrics:
                provider_metrics[prov_name] = {"calls": 0, "total_time": 0.0}
            provider_metrics[prov_name]["calls"] += 1
            provider_metrics[prov_name]["total_time"] += (job.generation_time or 0.0)
            
    return {
        "project_id": project_id,
        "status": project.status,
        "total_scenes": total_scenes,
        "completed_scenes": completed_scenes,
        "total_shots": total_shots,
        "completed_shots": completed_shots,
        "failed_shots": failed_shots,
        "current_scene": current_scene,
        "current_shot": current_shot,
        "provider_metrics": provider_metrics
    }

