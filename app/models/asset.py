from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Any, Dict, Optional
from app.database.base import Base

class Asset(Base):
    """SQLAlchemy model for assets."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    continuity_key: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    episode_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scene_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shot_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    generation_job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("generation_jobs.id", ondelete="SET NULL"), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(50), default="image", nullable=False)
    image_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    storage_provider: Mapped[str] = mapped_column(String(100), default="local", nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    generation_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prompt_hash: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    compiled_positive_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    compiled_negative_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generation_spec_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    collection_id: Mapped[Optional[int]] = mapped_column(ForeignKey("asset_collections.collection_id", ondelete="SET NULL"), nullable=True)

    project = relationship("Project")
    generation_job = relationship("GenerationJob")
    collection = relationship("AssetCollection", back_populates="assets", foreign_keys=[collection_id])
    tags = relationship("AssetTag", back_populates="asset", cascade="all, delete-orphan")
