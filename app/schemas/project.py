from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""

    title: str = Field(..., min_length=1, description="Project title (cannot be empty)")
    description: str | None = Field(None, description="Optional project description")


class ProjectResponse(BaseModel):
    """Schema for project API responses."""

    id: int
    title: str
    description: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
