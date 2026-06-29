from datetime import datetime

from pydantic import BaseModel, Field


class StoryCreate(BaseModel):
    """Schema for creating a new story."""

    title: str = Field(..., min_length=1, description="Story title (cannot be empty)")
    genre: str | None = Field(None, description="Optional genre")
    summary: str | None = Field(None, description="Optional summary")
    story_text: str | None = Field(None, description="Optional story text")


class StoryResponse(BaseModel):
    """Schema for story API responses."""

    id: int
    project_id: int
    title: str
    genre: str | None
    summary: str | None
    story_text: str | None
    status: str
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}
