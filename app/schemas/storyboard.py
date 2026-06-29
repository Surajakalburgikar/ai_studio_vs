from pydantic import BaseModel


class StoryboardShot(BaseModel):
    """Schema for a single shot in a storyboard."""

    shot_number: int
    shot_type: str
    camera_angle: str
    duration_seconds: float
    focus_characters: list[str]
    description: str
    transition: str


class StoryboardResponse(BaseModel):
    """Schema for a storyboard generation response."""

    scene_id: int
    scene_title: str
    project_id: int
    project_title: str
    shots: list[StoryboardShot]
