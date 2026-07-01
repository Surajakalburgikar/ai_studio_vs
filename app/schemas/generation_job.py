from datetime import datetime
from pydantic import BaseModel, Field


class GenerationJobCreate(BaseModel):
    """Schema for creating generation jobs."""

    scene_id: int = Field(..., description="The ID of the scene")
    provider: str | None = Field("mock", description="The image provider name")
    priority: int | None = Field(0, description="The job priority")


class GenerationJobProgress(BaseModel):
    """Schema for updating generation job progress."""

    progress: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")


class GenerationJobComplete(BaseModel):
    """Schema for completing a generation job."""

    drive_file_id: str | None = Field(None, description="Drive file ID")
    generation_time: float | None = Field(None, description="Time taken to generate the asset in seconds")
    provider: str | None = Field(None, description="The actual provider/transport/model used for generation")


class GenerationJobFailed(BaseModel):
    """Schema for failing a generation job."""

    error_message: str = Field(..., description="Error message describing the failure")


class GenerationJobResponse(BaseModel):
    """Schema for generation job API response."""

    id: int
    scene_id: int
    shot_number: int
    provider: str | None
    prompt: str
    negative_prompt: str | None
    filename: str | None
    status: str
    priority: int
    retry_count: int
    progress: int
    project_id: int | None = None
    scene_number: int | None = None
    drive_file_id: str | None
    generation_time: float | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
