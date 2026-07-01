from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

class AssetResponse(BaseModel):
    id: int
    continuity_key: Optional[str] = None
    project_id: Optional[int] = None
    episode_id: Optional[int] = None
    scene_id: Optional[int] = None
    shot_id: Optional[int] = None
    generation_job_id: Optional[int] = None
    asset_type: str
    image_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    storage_provider: str
    provider: Optional[str] = None
    model: Optional[str] = None
    seed: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    generation_time: Optional[float] = None
    prompt_hash: Optional[str] = None
    compiled_positive_prompt: Optional[str] = None
    compiled_negative_prompt: Optional[str] = None
    generation_spec_version: Optional[str] = None
    revision: int
    status: str
    created_at: datetime
    updated_at: datetime
    metadata_json: Dict[str, Any]

    model_config = {"from_attributes": True}


class AssetCollectionResponse(BaseModel):
    collection_id: int
    project_id: Optional[int] = None
    episode_id: Optional[int] = None
    scene_id: Optional[int] = None
    shot_number: Optional[int] = None
    continuity_key: Optional[str] = None
    collection_name: Optional[str] = None
    canonical_asset_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_json")

    model_config = {"from_attributes": True}


class AssetUsageResponse(BaseModel):
    usage_id: int
    asset_id: int
    project_id: Optional[int] = None
    episode_id: Optional[int] = None
    scene_id: Optional[int] = None
    purpose: str
    reference_id: Optional[str] = None
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_json")

    model_config = {"from_attributes": True}
