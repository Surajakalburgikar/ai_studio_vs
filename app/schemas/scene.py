from datetime import datetime

from pydantic import BaseModel, Field


class SceneCreate(BaseModel):
    """Schema for creating a new scene."""

    scene_number: int = Field(..., gt=0, description="Scene number (must be > 0)")
    title: str = Field(..., min_length=1, description="Scene title (cannot be empty)")
    narration: str | None = Field(None, description="Optional narration text")
    camera_notes: str | None = Field(None, description="Optional camera notes")
    duration_seconds: float | None = Field(
        None, gt=0, description="Optional duration in seconds (must be > 0)"
    )


class SceneResponse(BaseModel):
    """Schema for scene API responses."""

    id: int
    episode_id: int
    scene_number: int
    title: str
    narration: str | None
    camera_notes: str | None
    duration_seconds: float | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
