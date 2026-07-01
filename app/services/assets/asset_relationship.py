from enum import Enum
from dataclasses import dataclass
from typing import List, Optional

class RelationshipType(str, Enum):
    REFERENCE_TO_GENERATED = "reference_to_generated"  # e.g., Character reference -> Generated image
    GENERATED_TO_VIDEO = "generated_to_video"          # e.g., Image -> Video clip
    VIDEO_TO_FINAL = "video_to_final"                  # e.g., Video clip -> Final assembled video
    ASSET_TO_THUMBNAIL = "asset_to_thumbnail"          # e.g., Image/Video -> Thumbnail

@dataclass
class AssetRelationship:
    """Represents a directional relationship link between two assets."""
    source_asset_id: int
    target_asset_id: int
    relationship_type: RelationshipType
    metadata: Optional[dict] = None

class AssetRelationshipManager:
    """Hook/Abstraction for querying and managing asset lineage and dependency graphs."""
    
    def __init__(self, db_session = None) -> None:
        self.db = db_session
        self._relationships: List[AssetRelationship] = []

    def add_relationship(
        self, 
        source_id: int, 
        target_id: int, 
        rel_type: RelationshipType,
        metadata: Optional[dict] = None
    ) -> AssetRelationship:
        """Register a new relationship between two assets."""
        rel = AssetRelationship(
            source_asset_id=source_id,
            target_asset_id=target_id,
            relationship_type=rel_type,
            metadata=metadata
        )
        self._relationships.append(rel)
        # In the future, this will save to an asset_relationships DB table.
        return rel

    def get_downstream_assets(self, asset_id: int) -> List[AssetRelationship]:
        """Get all relationships where the given asset is the source (parent)."""
        return [r for r in self._relationships if r.source_asset_id == asset_id]

    def get_upstream_assets(self, asset_id: int) -> List[AssetRelationship]:
        """Get all relationships where the given asset is the target (child)."""
        return [r for r in self._relationships if r.target_asset_id == asset_id]
