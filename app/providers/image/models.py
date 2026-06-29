from typing import Any
from pydantic import BaseModel


class ImageResult(BaseModel):
    """Schema representing the result of an image generation task."""

    status: str
    provider: str
    image_path: str
    generation_time: float
    metadata: dict[str, Any]
