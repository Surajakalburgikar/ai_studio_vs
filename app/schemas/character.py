from datetime import datetime

from pydantic import BaseModel, Field


class CharacterCreate(BaseModel):
    """Schema for creating a new character."""

    name: str = Field(..., min_length=1, description="Character name (cannot be empty)")
    aliases: str | None = Field(None, description="Optional character aliases")
    role: str = Field(..., min_length=1, description="Character role (cannot be empty)")
    description: str | None = Field(None, description="Optional character description")
    age: str | None = Field(None, description="Optional character age")
    gender: str = Field(..., min_length=1, description="Character gender (cannot be empty)")
    species: str | None = Field(None, description="Optional character species")
    height_cm: int | None = Field(None, gt=0, description="Optional character height in cm (must be > 0)")
    body_type: str | None = Field(None, description="Optional character body type")
    hair_color: str | None = Field(None, description="Optional character hair color")
    hair_style: str | None = Field(None, description="Optional character hair style")
    eye_color: str | None = Field(None, description="Optional character eye color")
    skin_tone: str | None = Field(None, description="Optional character skin tone")
    face_description: str | None = Field(None, description="Optional character face description")
    clothing: str | None = Field(None, description="Optional character clothing description")
    accessories: str | None = Field(None, description="Optional character accessories description")
    personality: str | None = Field(None, description="Optional character personality description")
    art_style_override: str | None = Field(None, description="Optional character art style override")
    reference_prompt: str | None = Field(None, description="Optional character reference prompt")
    negative_prompt: str | None = Field(None, description="Optional character negative prompt")
    consistency_notes: str | None = Field(None, description="Optional character consistency notes")


class CharacterResponse(BaseModel):
    """Schema for character API responses."""

    id: int
    story_id: int
    name: str
    aliases: str | None
    role: str
    description: str | None
    age: str | None
    gender: str
    species: str | None
    height_cm: int | None
    body_type: str | None
    hair_color: str | None
    hair_style: str | None
    eye_color: str | None
    skin_tone: str | None
    face_description: str | None
    clothing: str | None
    accessories: str | None
    personality: str | None
    art_style_override: str | None
    reference_prompt: str | None
    negative_prompt: str | None
    consistency_notes: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
