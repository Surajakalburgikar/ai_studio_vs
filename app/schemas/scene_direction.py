from pydantic import BaseModel, Field

class TimelineEventSchema(BaseModel):
    timestamp: float = Field(..., description="Timestamp in seconds relative to the start of the shot")
    category: str = Field(..., description="Category of event (camera, character, environment, effects, audio, etc.)")
    action: str = Field(..., description="Action name (walk, smile, push_in, rain, bloom, etc.)")
    parameters: dict = Field(default_factory=dict, description="Arbitrary parameters dict")

    class Config:
        from_attributes = True

class KeyframeSchema(BaseModel):
    id: int = Field(..., description="Keyframe sequence ID")
    timestamp: float = Field(..., description="Keyframe timestamp in seconds relative to the start of the shot")
    description: str = Field(..., description="Keyframe description/purpose")

class ShotDirectionSchema(BaseModel):
    shot_number: int = Field(..., description="Shot number")
    shot_type: str = Field(..., description="Shot type (Wide, Medium, Close-up, etc.)")
    camera_angle: str = Field(..., description="Camera angle")
    duration_seconds: float = Field(..., description="Duration in seconds")
    focus_characters: list[str] = Field(..., description="List of focus characters")
    description: str = Field(..., description="Dynamic description")
    transition: str = Field(..., description="Transition style")
    timeline: list[TimelineEventSchema] = Field(..., description="Timeline events for this shot")
    estimated_keyframes: list[KeyframeSchema] = Field(..., description="Calculated keyframes")

class SceneDirectionResponse(BaseModel):
    scene_id: int = Field(..., description="Scene ID")
    scene_title: str = Field(..., description="Scene Title")
    narration: str | None = Field(None, description="Scene Narration")
    camera_notes: str | None = Field(None, description="Camera Notes")
    duration_seconds: float = Field(..., description="Scene Duration")
    shots: list[ShotDirectionSchema] = Field(..., description="List of directed shots")

class TimelineEventCreate(BaseModel):
    shot_number: int = Field(..., description="Shot number")
    timestamp: float = Field(..., description="Timestamp in seconds relative to the start of the shot")
    category: str = Field(..., description="Category of event")
    action: str = Field(..., description="Action of event")
    parameters: dict = Field(default_factory=dict, description="Arbitrary parameters")

class SceneDirectionUpdate(BaseModel):
    timeline_events: list[TimelineEventCreate] = Field(..., description="Custom timeline events to write")
