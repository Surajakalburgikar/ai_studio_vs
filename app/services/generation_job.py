import json
from sqlalchemy.orm import Session
from app.models.generation_job import GenerationJob
from app.prompt_engine.prompt_builder import build_prompts


def create_job_from_spec(
    db: Session, spec: "GenerationSpecification", priority: int = 0
) -> GenerationJob:
    """Convert a GenerationSpecification into a persisted GenerationJob."""
    from app.services.ai.models.generation_specification import GenerationSpecification
    shot_id = spec.prompt_bundle.shot_id
    try:
        parts = shot_id.split("_")
        scene_id = int(parts[0])
        shot_number = int(parts[1])
    except Exception:
        scene_id = 1
        shot_number = 1

    existing_job = db.query(GenerationJob).filter(
        GenerationJob.scene_id == scene_id,
        GenerationJob.shot_number == shot_number
    ).first()
    if existing_job:
        return existing_job

    spec_dict = {
        "job_id": spec.job_id,
        "provider": spec.provider,
        "model": spec.model,
        "compiled_positive_prompt": spec.compiled_positive_prompt,
        "compiled_negative_prompt": spec.compiled_negative_prompt,
        "generation_parameters": spec.generation_parameters,
        "output_configuration": spec.output_configuration,
        "storage_configuration": spec.storage_configuration,
        "version": spec.version,
        "metadata": spec.metadata,
    }

    serialized_spec = json.dumps(spec_dict)

    job = GenerationJob(
        scene_id=scene_id,
        shot_number=shot_number,
        provider=spec.provider,
        prompt=serialized_spec,
        negative_prompt=spec.compiled_negative_prompt,
        filename=spec.output_configuration.get("filename") or f"scene_{scene_id}_shot_{shot_number}.png",
        status="pending",
        priority=priority,
        retry_count=0,
        progress=0,
        drive_file_id=None,
        generation_time=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


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
        existing = db.query(GenerationJob).filter(
            GenerationJob.scene_id == scene_id,
            GenerationJob.shot_number == shot["shot_number"]
        ).first()
        if existing:
            created_jobs.append(existing)
            continue
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


def get_continuity_key_for_job(db: Session, job: GenerationJob) -> tuple[str | None, int | None]:
    try:
        scene = job.scene
        if not scene:
            from app.models.scene import Scene
            scene = db.query(Scene).filter(Scene.id == job.scene_id).first()
        if scene:
            episode = scene.episode
            if not episode:
                from app.models.episode import Episode
                episode = db.query(Episode).filter(Episode.id == scene.episode_id).first()
            if episode:
                story = episode.story
                if not story:
                    from app.models.story import Story
                    story = db.query(Story).filter(Story.id == episode.story_id).first()
                if story:
                    project = story.project
                    if not project:
                        from app.models.project import Project
                        project = db.query(Project).filter(Project.id == story.project_id).first()
                    if project:
                        return project.continuity_key, project.id
    except Exception:
        pass
    return None, None


def _update_checkpoint_for_job(db: Session, job: GenerationJob, step: str) -> None:
    continuity_key, project_id = get_continuity_key_for_job(db, job)
    if not continuity_key:
        return
        
    from app.services.ai.orchestrator.production_orchestrator import ProductionOrchestrator
    from app.services.ai.orchestrator.production_checkpoint import ProductionCheckpoint
    
    orchestrator = ProductionOrchestrator(db)
    checkpoint = orchestrator.state_manager.load_checkpoint(continuity_key)
    
    scene_number = 1
    episode_id = None
    try:
        if job.scene:
            scene_number = job.scene.scene_number
            episode_id = job.scene.episode_id
    except Exception:
        pass

    if not checkpoint:
        checkpoint = ProductionCheckpoint(
            continuity_key=continuity_key,
            project_id=project_id,
            scene_id=job.scene_id,
            last_completed_step=step,
            last_completed_shot_number=job.shot_number,
            last_completed_scene_number=scene_number,
            episode_id=episode_id,
            status="active"
        )
    else:
        checkpoint.last_completed_step = step
        checkpoint.last_completed_shot_number = max(checkpoint.last_completed_shot_number, job.shot_number)
        checkpoint.scene_id = job.scene_id
        checkpoint.job_id = job.id
        checkpoint.provider = job.provider or checkpoint.provider
        checkpoint.output_path = job.drive_file_id or checkpoint.output_path
        checkpoint.generation_time = job.generation_time or checkpoint.generation_time
        checkpoint.retry_count = job.retry_count
        if episode_id:
            checkpoint.episode_id = episode_id
        checkpoint.last_completed_scene_number = max(checkpoint.last_completed_scene_number, scene_number)
        
    orchestrator.record_checkpoint(checkpoint)


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
        _update_checkpoint_for_job(db, job, "job_started")
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
            _update_checkpoint_for_job(db, job, "job_started")
        else:
            db.commit()
            db.refresh(job)
            
        # Determine checkpoint step depending on progress range
        if progress == 50:
            _update_checkpoint_for_job(db, job, "image_generated")
        elif progress == 80:
            _update_checkpoint_for_job(db, job, "image_saved")
    return job


def write_project_production_summary(db: Session, project_id: int) -> None:
    from app.models.project import Project
    from app.models.scene import Scene
    from app.models.episode import Episode
    from app.models.story import Story
    from app.models.generation_job import GenerationJob
    from app.models.asset import Asset
    import json
    import os
    from pathlib import Path

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return

    # Fetch all jobs for scenes in this project
    jobs = (
        db.query(GenerationJob)
        .join(Scene)
        .join(Episode)
        .join(Story)
        .filter(Story.project_id == project_id)
        .all()
    )

    total_shots = len(jobs)
    completed_jobs = [j for j in jobs if j.status == "completed"]
    failed_jobs = [j for j in jobs if j.status == "failed"]
    completed_shots = len(completed_jobs)
    failed_shots = len(failed_jobs)
    
    success_rate = (completed_shots / total_shots * 100.0) if total_shots > 0 else 0.0
    total_gen_time = sum(j.generation_time or 0.0 for j in jobs)

    # Collect assets info
    assets_list = []
    for job in completed_jobs:
        asset = db.query(Asset).filter(Asset.generation_job_id == job.id).first()
        assets_list.append({
            "asset_id": asset.id if asset else None,
            "scene_number": job.scene_number or job.scene_id,
            "shot_number": job.shot_number,
            "path": job.drive_file_id or job.filename,
            "generation_time": job.generation_time
        })

    summary_data = {
        "project_id": project.id,
        "title": project.title,
        "total_scenes": db.query(Scene).join(Episode).join(Story).filter(Story.project_id == project_id).count(),
        "total_shots": total_shots,
        "completed_shots": completed_shots,
        "failed_shots": failed_shots,
        "success_rate": success_rate,
        "total_generation_time_seconds": total_gen_time,
        "assets": assets_list
    }

    # Write to generated/Project_XXX/production_summary.json
    for base_path_str in [".", "../AI_STUDIO_WORKER"]:
        base_path = Path(base_path_str).resolve()
        if os.path.exists(base_path):
            project_dir = base_path / "generated" / f"Project_{project.id:03d}"
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # Write JSON summary
            json_file = project_dir / "production_summary.json"
            try:
                with open(json_file, "w") as f:
                    json.dump(summary_data, f, indent=2)
            except Exception as e:
                print(f"Failed to write production summary json to {json_file}: {e}")

            # Write MD summary
            md_file = project_dir / "production_summary.md"
            try:
                with open(md_file, "w") as f:
                    f.write(f"# Production Summary for Project: {project.title}\n\n")
                    f.write(f"- **Project ID**: {project.id}\n")
                    f.write(f"- **Total Shots**: {total_shots}\n")
                    f.write(f"- **Completed Shots**: {completed_shots}\n")
                    f.write(f"- **Failed Shots**: {failed_shots}\n")
                    f.write(f"- **Success Rate**: {success_rate:.1f}%\n")
                    f.write(f"- **Total Generation Time**: {total_gen_time:.2f} seconds\n\n")
                    f.write("## Generated Assets\n\n")
                    f.write("| Scene | Shot | Asset ID | File Path | Gen Time |\n")
                    f.write("| --- | --- | --- | --- | --- |\n")
                    for a in assets_list:
                        f.write(f"| {a['scene_number']} | {a['shot_number']} | {a['asset_id']} | `{a['path']}` | {a['generation_time']:.2f}s |\n")
            except Exception as e:
                print(f"Failed to write production summary md to {md_file}: {e}")


def check_and_update_project_status(db: Session, project_id: int) -> None:
    from app.models.project import Project
    from app.models.scene import Scene
    from app.models.episode import Episode
    from app.models.story import Story

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return

    # Fetch all scenes for this project
    scenes = (
        db.query(Scene)
        .join(Episode)
        .join(Story)
        .filter(Story.project_id == project_id)
        .all()
    )
    if not scenes:
        return

    # Check if all scenes are complete
    all_scenes_complete = all(s.status == "completed" for s in scenes)
    if all_scenes_complete:
        project.status = "completed"
        db.commit()
        write_project_production_summary(db, project_id)


def check_and_update_scene_status(db: Session, scene_id: int) -> None:
    from app.models.scene import Scene
    from app.models.generation_job import GenerationJob
    from app.models.asset import Asset
    import json
    import os
    from pathlib import Path

    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        return

    # Fetch all jobs for this scene
    jobs = db.query(GenerationJob).filter(GenerationJob.scene_id == scene_id).all()
    if not jobs:
        return

    # Check if all jobs are terminal (completed or failed)
    all_terminal = all(j.status in ["completed", "failed"] for j in jobs)
    if not all_terminal:
        return

    scene.status = "completed"
    db.commit()

    # Collect scene details for metadata.json
    shot_list = []
    asset_ids = []
    generation_times = {}
    
    for job in jobs:
        asset = db.query(Asset).filter(Asset.generation_job_id == job.id).first()
        asset_id = asset.id if asset else None
        if asset_id:
            asset_ids.append(asset_id)
            
        shot_info = {
            "shot_number": job.shot_number,
            "status": job.status,
            "error_message": job.error_message,
            "filename": job.filename,
            "asset_id": asset_id,
            "generation_time": job.generation_time
        }
        shot_list.append(shot_info)
        
        if job.generation_time is not None:
            generation_times[f"shot_{job.shot_number}"] = job.generation_time

    metadata = {
        "scene_id": scene.id,
        "scene_number": scene.scene_number,
        "title": scene.title,
        "status": "completed",
        "shot_list": shot_list,
        "asset_ids": asset_ids,
        "generation_times": generation_times
    }

    # Write to generated/Project_XXX/Scene_YYY/metadata.json
    proj_id = 0
    try:
        proj_id = scene.episode.story.project_id
    except Exception:
        pass

    for base_path_str in [".", "../AI_STUDIO_WORKER"]:
        base_path = Path(base_path_str).resolve()
        if os.path.exists(base_path):
            meta_dir = base_path / "generated" / f"Project_{proj_id:03d}" / f"Scene_{scene.scene_number:03d}"
            meta_dir.mkdir(parents=True, exist_ok=True)
            meta_file = meta_dir / "metadata.json"
            try:
                with open(meta_file, "w") as f:
                    json.dump(metadata, f, indent=2)
            except Exception as e:
                print(f"Failed to write metadata.json to {meta_file}: {e}")

    # Check and update project status
    check_and_update_project_status(db, proj_id)


def complete_job(
    db: Session,
    job_id: int,
    drive_file_id: str | None = None,
    generation_time: float | None = None,
    provider: str | None = None,
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
        if provider is not None:
            job.provider = provider
        db.commit()
        db.refresh(job)
        
        try:
            from app.services.assets.asset_manager import AssetManager
            AssetManager(db).register_completed_job(job)
        except Exception as e:
            print(f"Failed to register asset: {e}")

        _update_checkpoint_for_job(db, job, "callback_received")
        _update_checkpoint_for_job(db, job, "job_completed")

        # Check and update scene status
        try:
            check_and_update_scene_status(db, job.scene_id)
        except Exception as e:
            print(f"Failed to update scene/project status: {e}")

    return job


def is_retryable_error(error_message: str) -> bool:
    err_msg = error_message.lower()
    # Never retry: 401, 403, 400
    if "401" in err_msg or "403" in err_msg or "400" in err_msg or "unauthorized" in err_msg or "bad request" in err_msg or "auth" in err_msg:
        return False
    # Retry: 429, Timeout, Temporary provider unavailable, Network failure
    if "429" in err_msg or "timeout" in err_msg or "timed out" in err_msg or "rate limit" in err_msg or "too many requests" in err_msg:
        return True
    if "unavailable" in err_msg or "network" in err_msg or "connection" in err_msg or "dns" in err_msg:
        return True
    return False


def mark_failed(
    db: Session,
    job_id: int,
    error_message: str,
) -> GenerationJob | None:
    """Mark a generation job as failed and save the error message, retrying if retryable."""
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if job:
        max_retries = 3
        if job.retry_count < max_retries and is_retryable_error(error_message):
            job.retry_count += 1
            job.status = "pending"
            job.progress = 0
            job.error_message = f"Retry {job.retry_count}: {error_message}"
            db.commit()
            db.refresh(job)
            _update_checkpoint_for_job(db, job, f"job_retry_{job.retry_count}")
        else:
            job.status = "failed"
            job.error_message = error_message
            db.commit()
            db.refresh(job)
            _update_checkpoint_for_job(db, job, "job_failed")

        # After updating the job status, check scene status
        try:
            check_and_update_scene_status(db, job.scene_id)
        except Exception as e:
            print(f"Failed to update scene/project status: {e}")

    return job
