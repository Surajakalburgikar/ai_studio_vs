from datetime import datetime

from pydantic import BaseModel, Field

from app.models.project import VideoType, AspectRatio, ArtStyle, NarrationStyle, VoiceGender


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""

    title: str = Field(..., min_length=1, description="Project title (cannot be empty)")
    description: str | None = Field(None, description="Optional project description")
    video_type: VideoType = Field(default=VideoType.MEDIUM, description="Video type configuration")
    target_duration_seconds: int = Field(default=180, gt=0, description="Target duration in seconds (must be > 0)")
    aspect_ratio: AspectRatio = Field(default=AspectRatio.SIXTEEN_TO_NINE, description="Aspect ratio configuration")
    language: str = Field(default="English", description="Primary language")
    art_style: ArtStyle = Field(default=ArtStyle.ANIME, description="Art style configuration")
    narration_style: NarrationStyle = Field(default=NarrationStyle.THIRD_PERSON, description="Narration style configuration")
    subtitle_language: str = Field(default="English", description="Subtitle language")
    voice_gender: VoiceGender = Field(default=VoiceGender.MALE, description="Voice gender configuration")
    preferred_story_model: str | None = Field(default=None, description="Preferred story model")


class ProjectResponse(BaseModel):
    """Schema for project API responses."""

    id: int
    title: str
    description: str | None
    status: str
    created_at: datetime
    video_type: VideoType
    target_duration_seconds: int
    aspect_ratio: AspectRatio
    language: str
    art_style: ArtStyle
    narration_style: NarrationStyle
    subtitle_language: str
    voice_gender: VoiceGender
    preferred_story_model: str | None = None

    model_config = {"from_attributes": True}

