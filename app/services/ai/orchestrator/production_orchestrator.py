import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.project import Project
from app.services.ai.continuity.continuity_manager import ContinuityManager
from .production_run import ProductionRun
from .production_checkpoint import ProductionCheckpoint
from .production_state import ProductionStateManager

class ProductionOrchestrator:
    """Orchestrates production runs, resumes, continuations, checkpoints, and quality policy adherence."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.continuity_manager = ContinuityManager()
        self.state_manager = ProductionStateManager()

    def start_production(self, project_id: int) -> ProductionRun:
        """Start a brand new production run for a project. Generates a new continuity key if not already linked."""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found.")

        if not project.continuity_key:
            project.continuity_key = f"con_{uuid.uuid4().hex[:12]}"
            self.db.commit()

        continuity_key = project.continuity_key

        manifest = self.continuity_manager.load_manifest(continuity_key)
        if not manifest:
            manifest = self.continuity_manager.create_new_manifest(
                continuity_key=continuity_key,
                series_title=project.title,
                universe_title=f"Universe for {project.title}"
            )

        manifest.last_project_id = project_id
        self.continuity_manager.save_manifest(manifest)

        run_id = f"run_{uuid.uuid4().hex[:12]}"
        checkpoint = ProductionCheckpoint(
            continuity_key=continuity_key,
            project_id=project_id,
            scene_id=0,
            last_completed_step="started",
            last_completed_shot_number=0,
            last_completed_scene_number=0,
            status="active"
        )
        run = ProductionRun(
            run_id=run_id,
            continuity_key=continuity_key,
            project_id=project_id,
            status="active",
            checkpoint=checkpoint
        )
        self.state_manager.save_run(run)
        self.state_manager.save_checkpoint(checkpoint)
        return run

    def resume_production(self, continuity_key: str) -> ProductionRun:
        """Resume an existing production run from the last recorded checkpoint."""
        run = self.state_manager.load_run_by_continuity_key(continuity_key)
        if not run:
            raise ValueError(f"No active run found for continuity key: {continuity_key}")

        checkpoint = self.state_manager.load_checkpoint(continuity_key)
        if checkpoint:
            checkpoint.status = "active"
            run.checkpoint = checkpoint
            self.state_manager.save_checkpoint(checkpoint)

        run.status = "active"
        run.updated_at = datetime.utcnow().isoformat()
        self.state_manager.save_run(run)

        # Transition paused jobs back to pending
        from app.models.generation_job import GenerationJob
        from app.models.scene import Scene
        from app.models.episode import Episode
        from app.models.story import Story
        
        jobs = (
            self.db.query(GenerationJob)
            .join(Scene)
            .join(Episode)
            .join(Story)
            .filter(Story.project_id == run.project_id)
            .filter(GenerationJob.status == "paused")
            .all()
        )
        for job in jobs:
            job.status = "pending"
        self.db.commit()

        return run

    def continue_as_new_project(self, from_project_id: int, new_project_id: int) -> ProductionRun:
        """Continue a story universe from an existing project into a new project (e.g. Part 2 / sequel).
        
        Sprint 29.1: The continuity_key is SHARED across all projects in the same series.
        A revision entry is appended to record the story continuation instead of cloning the manifest.
        """
        from_project = self.db.query(Project).filter(Project.id == from_project_id).first()
        new_project  = self.db.query(Project).filter(Project.id == new_project_id).first()

        if not from_project:
            raise ValueError(f"Source project {from_project_id} not found.")
        if not new_project:
            raise ValueError(f"Destination project {new_project_id} not found.")

        continuity_key = from_project.continuity_key
        if not continuity_key:
            continuity_key = f"con_{uuid.uuid4().hex[:12]}"
            from_project.continuity_key = continuity_key
            self.db.commit()

        # Both projects share the SAME continuity_key — no clone, just a new revision
        new_project.continuity_key = continuity_key
        self.db.commit()

        manifest = self.continuity_manager.load_manifest(continuity_key)
        if not manifest:
            manifest = self.continuity_manager.create_new_manifest(
                continuity_key=continuity_key,
                series_title=from_project.title
            )

        # Record the continuation as a revision entry
        self.continuity_manager.add_revision(
            continuity_key=continuity_key,
            reason=f"Continued into project {new_project_id}",
            author="system",
            summary=f"Story universe continued from project {from_project_id} to project {new_project_id}",
            project_id=new_project_id,
        )

        return self.start_production(new_project_id)

    def pause_production(self, continuity_key: str, reason: str) -> ProductionRun:
        """Pause a running production. Updates status and logs the reason in metadata."""
        run = self.state_manager.load_run_by_continuity_key(continuity_key)
        if not run:
            raise ValueError(f"No run found for continuity key: {continuity_key}")

        run.status = "paused"
        run.metadata["pause_reason"] = reason
        run.updated_at = datetime.utcnow().isoformat()

        checkpoint = self.state_manager.load_checkpoint(continuity_key)
        if checkpoint:
            checkpoint.status = "paused"
            checkpoint.metadata["pause_reason"] = reason
            run.checkpoint = checkpoint
            self.state_manager.save_checkpoint(checkpoint)

        # Transition pending and processing jobs to paused
        from app.models.generation_job import GenerationJob
        from app.models.scene import Scene
        from app.models.episode import Episode
        from app.models.story import Story
        
        jobs = (
            self.db.query(GenerationJob)
            .join(Scene)
            .join(Episode)
            .join(Story)
            .filter(Story.project_id == run.project_id)
            .filter(GenerationJob.status.in_(["pending", "processing"]))
            .all()
        )
        for job in jobs:
            job.status = "paused"
        self.db.commit()

        self.state_manager.save_run(run)
        return run

    def record_checkpoint(self, checkpoint: ProductionCheckpoint) -> None:
        """Persist a new production progress checkpoint and update the associated run."""
        self.state_manager.save_checkpoint(checkpoint)
        
        run = self.state_manager.load_run_by_continuity_key(checkpoint.continuity_key)
        if run:
            run.checkpoint = checkpoint
            run.updated_at = datetime.utcnow().isoformat()
            self.state_manager.save_run(run)

        self.continuity_manager.update_after_completed_step(
            continuity_key=checkpoint.continuity_key,
            project_id=checkpoint.project_id,
            episode_number=checkpoint.episode_id,
            scene_number=checkpoint.last_completed_scene_number,
            shot_number=checkpoint.last_completed_shot_number
        )

    def finish_production(self, continuity_key: str) -> ProductionRun:
        """Mark a production run as completed."""
        run = self.state_manager.load_run_by_continuity_key(continuity_key)
        if not run:
            raise ValueError(f"No run found for continuity key: {continuity_key}")

        run.status = "completed"
        run.updated_at = datetime.utcnow().isoformat()

        checkpoint = self.state_manager.load_checkpoint(continuity_key)
        if checkpoint:
            checkpoint.status = "completed"
            checkpoint.last_completed_step = "completed"
            run.checkpoint = checkpoint
            self.state_manager.save_checkpoint(checkpoint)

        self.state_manager.save_run(run)
        return run
