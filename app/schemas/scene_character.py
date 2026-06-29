from pydantic import BaseModel


class SceneCharacterAssign(BaseModel):
    """Schema for assigning character to scene."""

    scene_id: int
    character_id: int


class SceneCharacterResponse(BaseModel):
    """Schema for scene character mapping response."""

    scene_id: int
    character_id: int

    model_config = {"from_attributes": True}
