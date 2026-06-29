from datetime import datetime

from pydantic import BaseModel, Field


class EpisodeCreate(BaseModel):
    """Schema for creating a new episode."""

    episode_number: int = Field(..., gt=0, description="Episode number (must be > 0)")
    title: str = Field(..., min_length=1, description="Episode title (cannot be empty)")
    summary: str | None = Field(None, description="Optional episode summary")


class EpisodeResponse(BaseModel):
    """Schema for episode API responses."""

    id: int
    story_id: int
    episode_number: int
    title: str
    summary: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
