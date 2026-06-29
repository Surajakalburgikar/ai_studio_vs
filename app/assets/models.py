from typing import Any
from pydantic import BaseModel


class AssetResponse(BaseModel):
    """Schema representing existing assets and manifest under a scene directory."""

    directory: str
    existing_files: list[str]
    manifest: dict[str, Any]
