from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

class AssetType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    REFERENCE = "reference"
    THUMBNAIL = "thumbnail"

@dataclass
class Asset:
    """Production-grade representation of a generated production asset."""
    asset_id: int
    asset_type: AssetType
    continuity_key: Optional[str]
    project_id: Optional[int]
    episode_id: Optional[int]
    scene_id: Optional[int]
    shot_id: Optional[int]
    generation_job_id: Optional[int]
    revision_number: int
    status: str
    provider: Optional[str]
    model: Optional[str]
    seed: Optional[int]
    compiled_prompt: Optional[str]
    compiled_negative_prompt: Optional[str]
    generation_spec_version: Optional[str]
    storage_provider: str
    relative_path: Optional[str]
    thumbnail_path: Optional[str]
    width: Optional[int]
    height: Optional[int]
    aspect_ratio: Optional[str]
    file_size: Optional[int]
    generation_time: Optional[float]
    checksum: Optional[str]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_db_model(cls, db_model) -> "Asset":
        """Convert SQLAlchemy Asset model to this dataclass."""
        if not db_model:
            return None
        
        # Calculate aspect ratio dynamically if not stored, or use width/height
        aspect_ratio = None
        if db_model.width and db_model.height:
            aspect_ratio = f"{db_model.width}:{db_model.height}"
            
        return cls(
            asset_id=db_model.id,
            asset_type=AssetType(db_model.asset_type),
            continuity_key=db_model.continuity_key,
            project_id=db_model.project_id,
            episode_id=db_model.episode_id,
            scene_id=db_model.scene_id,
            shot_id=db_model.shot_id,
            generation_job_id=db_model.generation_job_id,
            revision_number=db_model.revision,
            status=db_model.status,
            provider=db_model.provider,
            model=db_model.model,
            seed=db_model.seed,
            compiled_prompt=db_model.compiled_positive_prompt,
            compiled_negative_prompt=db_model.compiled_negative_prompt,
            generation_spec_version=db_model.generation_spec_version,
            storage_provider=db_model.storage_provider,
            relative_path=db_model.image_path,
            thumbnail_path=db_model.thumbnail_path,
            width=db_model.width,
            height=db_model.height,
            aspect_ratio=aspect_ratio,
            file_size=db_model.file_size,
            generation_time=db_model.generation_time,
            checksum=db_model.prompt_hash,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at,
            metadata=db_model.metadata_json or {}
        )
