from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class AssetCollection(Base):
    __tablename__ = "asset_collections"

    collection_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    episode_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scene_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shot_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    continuity_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    collection_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    canonical_asset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    project = relationship("Project")
    canonical_asset = relationship("Asset", foreign_keys=[canonical_asset_id])
    assets = relationship("Asset", back_populates="collection", foreign_keys="Asset.collection_id")


