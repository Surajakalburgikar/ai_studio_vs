from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.asset import Asset
from .asset_status import AssetStatus
from .asset_revision import mark_revision_canonical

class AssetRepository:
    """Handles lookups and retrieval of assets under various query filters."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, asset_id: int) -> Optional[Asset]:
        """Retrieve asset by its primary key ID."""
        return self.db.query(Asset).filter(Asset.id == asset_id).first()

    def find_assets(
        self,
        continuity_key: Optional[str] = None,
        project_id: Optional[int] = None,
        episode_id: Optional[int] = None,
        scene_id: Optional[int] = None,
        shot_id: Optional[int] = None,
        generation_job_id: Optional[int] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        status: Optional[str] = None,
        revision: Optional[int] = None
    ) -> List[Asset]:
        """Filter assets by multiple attributes."""
        query = self.db.query(Asset)
        if continuity_key is not None:
            query = query.filter(Asset.continuity_key == continuity_key)
        if project_id is not None:
            query = query.filter(Asset.project_id == project_id)
        if episode_id is not None:
            query = query.filter(Asset.episode_id == episode_id)
        if scene_id is not None:
            query = query.filter(Asset.scene_id == scene_id)
        if shot_id is not None:
            query = query.filter(Asset.shot_id == shot_id)
        if generation_job_id is not None:
            query = query.filter(Asset.generation_job_id == generation_job_id)
        if provider is not None:
            query = query.filter(Asset.provider == provider)
        if model is not None:
            query = query.filter(Asset.model == model)
        if status is not None:
            query = query.filter(Asset.status == status)
        if revision is not None:
            query = query.filter(Asset.revision == revision)
            
        return query.order_by(Asset.revision.desc()).all()

    # ── Task 4 Revision System Methods ──────────────────────────────────────

    def latest_revision(self, project_id: int, scene_id: int, shot_id: int) -> Optional[Asset]:
        """Retrieve the latest revision for a given shot."""
        return self.db.query(Asset).filter(
            Asset.project_id == project_id,
            Asset.scene_id == scene_id,
            Asset.shot_id == shot_id
        ).order_by(Asset.revision.desc()).first()

    def approved_revision(self, project_id: int, scene_id: int, shot_id: int) -> Optional[Asset]:
        """Retrieve the approved (canonical) revision for a given shot."""
        return self.db.query(Asset).filter(
            Asset.project_id == project_id,
            Asset.scene_id == scene_id,
            Asset.shot_id == shot_id,
            Asset.status == AssetStatus.APPROVED
        ).first()

    def revision_history(self, project_id: int, scene_id: int, shot_id: int) -> List[Asset]:
        """Retrieve all revisions for a given shot ordered by revision ascending."""
        return self.db.query(Asset).filter(
            Asset.project_id == project_id,
            Asset.scene_id == scene_id,
            Asset.shot_id == shot_id
        ).order_by(Asset.revision.asc()).all()

    def mark_canonical(self, asset_id: int) -> Asset:
        """Mark a specific asset revision as canonical/approved."""
        return mark_revision_canonical(self.db, asset_id)

    # ── Backward compatibility wrappers ──────────────────────────────────────

    def get_latest_revision(self, project_id: int, scene_id: int, shot_id: int) -> Optional[Asset]:
        return self.latest_revision(project_id, scene_id, shot_id)

    def get_approved_revision(self, project_id: int, scene_id: int, shot_id: int) -> Optional[Asset]:
        return self.approved_revision(project_id, scene_id, shot_id)

    def get_all_revisions(self, project_id: int, scene_id: int, shot_id: int) -> List[Asset]:
        return self.revision_history(project_id, scene_id, shot_id)
