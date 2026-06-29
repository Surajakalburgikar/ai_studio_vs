from pydantic import BaseModel


class PromptShot(BaseModel):
    """Schema for prompt details of a single shot."""

    shot_number: int
    positive_prompt: str
    negative_prompt: str
    image_filename: str


class PromptResponse(BaseModel):
    """Schema for prompt generator response."""

    scene_id: int
    scene_title: str
    project_id: int
    project_title: str
    shots: list[PromptShot]
