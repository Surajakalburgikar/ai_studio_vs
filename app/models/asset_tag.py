from sqlalchemy import ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class AssetTag(Base):
    __tablename__ = "asset_tags"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Relationship
    asset = relationship("Asset", back_populates="tags")
