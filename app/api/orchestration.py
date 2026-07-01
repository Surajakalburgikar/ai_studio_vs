from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.ai.orchestrator.production_orchestrator import ProductionOrchestrator
from app.services.ai.continuity.continuity_manager import ContinuityManager

router = APIRouter(prefix="/production", tags=["orchestration"])

# ── Existing lifecycle endpoints ────────────────────────────────────────────

@router.post("/start", response_model=dict)
def start_production(project_id: int = Query(...), db: Session = Depends(get_db)):
    """Start a production run for a given project."""
    orchestrator = ProductionOrchestrator(db)
    try:
        run = orchestrator.start_production(project_id)
        return run.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{continuity_key}/pause", response_model=dict)
def pause_production(continuity_key: str, reason: str = "paused by user", db: Session = Depends(get_db)):
    """Pause an active production run."""
    orchestrator = ProductionOrchestrator(db)
    try:
        run = orchestrator.pause_production(continuity_key, reason)
        return run.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{continuity_key}/resume", response_model=dict)
def resume_production(continuity_key: str, db: Session = Depends(get_db)):
    """Resume a paused production run."""
    orchestrator = ProductionOrchestrator(db)
    try:
        run = orchestrator.resume_production(continuity_key)
        return run.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/continue-project", response_model=dict)
def continue_project(
    from_project_id: int = Query(...),
    new_project_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Continue a story universe (continuity key) into a new project."""
    orchestrator = ProductionOrchestrator(db)
    try:
        run = orchestrator.continue_as_new_project(from_project_id, new_project_id)
        return run.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Existing query endpoints ────────────────────────────────────────────────

@router.get("/{continuity_key}/manifest", response_model=dict)
def get_manifest(continuity_key: str, db: Session = Depends(get_db)):
    """Fetch the continuity manifest for a given universe key."""
    orchestrator = ProductionOrchestrator(db)
    manifest = orchestrator.continuity_manager.load_manifest(continuity_key)
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")
    return manifest.to_dict()


@router.get("/{continuity_key}/checkpoint", response_model=dict)
def get_checkpoint(continuity_key: str, db: Session = Depends(get_db)):
    """Fetch the latest production checkpoint for a given universe key."""
    orchestrator = ProductionOrchestrator(db)
    checkpoint = orchestrator.state_manager.load_checkpoint(continuity_key)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return checkpoint.to_dict()


@router.get("/{continuity_key}/status", response_model=dict)
def get_status(continuity_key: str, db: Session = Depends(get_db)):
    """Fetch the current production run status for a given universe key."""
    orchestrator = ProductionOrchestrator(db)
    run = orchestrator.state_manager.load_run_by_continuity_key(continuity_key)
    if not run:
        raise HTTPException(status_code=404, detail="Active run not found")
    return run.to_dict()


# ── Sprint 29.1 — Revision History endpoints ───────────────────────────────

@router.get("/{continuity_key}/revisions", response_model=list)
def get_revision_history(continuity_key: str, db: Session = Depends(get_db)):
    """Return the full revision history for a continuity universe, oldest first."""
    mgr = ContinuityManager()
    revisions = mgr.list_revisions(continuity_key)
    return [r.to_dict() for r in revisions]


@router.get("/{continuity_key}/revisions/current", response_model=dict)
def get_current_revision(continuity_key: str, db: Session = Depends(get_db)):
    """Return the most recent revision entry for a continuity universe."""
    mgr = ContinuityManager()
    revisions = mgr.list_revisions(continuity_key)
    if not revisions:
        raise HTTPException(status_code=404, detail="No revisions found")
    return revisions[-1].to_dict()


@router.post("/{continuity_key}/revisions/{revision_number}/restore", response_model=dict)
def restore_revision(continuity_key: str, revision_number: int, db: Session = Depends(get_db)):
    """Restore the manifest canonical data to a specific past revision.
    
    A new revision entry is appended to record the restore action.
    The continuity_key never changes.
    """
    mgr = ContinuityManager()
    try:
        manifest = mgr.restore_revision(continuity_key, revision_number)
        return manifest.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Sprint 29.1 — Character state endpoints ────────────────────────────────

@router.get("/{continuity_key}/characters/{character_name}/identity", response_model=dict)
def get_character_identity(continuity_key: str, character_name: str, db: Session = Depends(get_db)):
    """Return the canonical (immutable) identity of a character."""
    from app.services.ai.continuity.continuity_resolver import ContinuityResolver
    mgr = ContinuityManager()
    manifest = mgr.load_manifest(continuity_key)
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")
    resolver = ContinuityResolver()
    canon = resolver.get_canonical_character(manifest, character_name)
    if not canon:
        raise HTTPException(status_code=404, detail=f"Character '{character_name}' not in manifest")
    return canon.to_dict()


@router.get("/{continuity_key}/characters/{character_name}/state", response_model=dict)
def get_character_state(continuity_key: str, character_name: str, db: Session = Depends(get_db)):
    """Return the latest runtime state of a character (outfit, expression, location …)."""
    from app.services.ai.continuity.continuity_resolver import ContinuityResolver
    mgr = ContinuityManager()
    manifest = mgr.load_manifest(continuity_key)
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")
    resolver = ContinuityResolver()
    state = resolver.get_character_state(manifest, character_name)
    if not state:
        raise HTTPException(status_code=404, detail=f"No state found for character '{character_name}'")
    return state.to_dict()


# ── Sprint 29.1 — Narrative timeline endpoint ──────────────────────────────

@router.get("/{continuity_key}/timeline", response_model=dict)
def get_timeline(continuity_key: str, db: Session = Depends(get_db)):
    """Return the narrative timeline for a continuity universe."""
    mgr = ContinuityManager()
    timeline = mgr.load_timeline(continuity_key)
    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")
    return timeline.to_dict()
