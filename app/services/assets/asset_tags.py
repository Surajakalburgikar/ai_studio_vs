from typing import List
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.asset import Asset
from app.models.asset_tag import AssetTag

class AssetTagManager:
    """Manages searchable tags for assets with case-insensitivity and uniqueness."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def add_tag(self, asset_id: int, tag: str) -> None:
        """Add a tag to an asset. Removes duplicates case-insensitively."""
        tag_norm = tag.strip().lower()
        if not tag_norm:
            return
        
        existing = self.db.query(AssetTag).filter(
            AssetTag.asset_id == asset_id,
            func.lower(AssetTag.tag) == tag_norm
        ).first()
        
        if not existing:
            new_tag = AssetTag(asset_id=asset_id, tag=tag.strip())
            self.db.add(new_tag)
            self.db.commit()

    def remove_tag(self, asset_id: int, tag: str) -> None:
        """Remove a tag from an asset case-insensitively."""
        tag_norm = tag.strip().lower()
        self.db.query(AssetTag).filter(
            AssetTag.asset_id == asset_id,
            func.lower(AssetTag.tag) == tag_norm
        ).delete(synchronize_session=False)
        self.db.commit()

    def replace_tags(self, asset_id: int, tags: List[str]) -> None:
        """Replace all tags for an asset with a new list, removing duplicates."""
        self.db.query(AssetTag).filter(AssetTag.asset_id == asset_id).delete(synchronize_session=False)
        self.db.commit()

        seen = set()
        for t in tags:
            t_clean = t.strip()
            t_lower = t_clean.lower()
            if t_lower and t_lower not in seen:
                seen.add(t_lower)
                new_tag = AssetTag(asset_id=asset_id, tag=t_clean)
                self.db.add(new_tag)
        self.db.commit()

    def list_tags(self, asset_id: int) -> List[str]:
        """List all tags for an asset."""
        rows = self.db.query(AssetTag).filter(AssetTag.asset_id == asset_id).all()
        return [r.tag for r in rows]

    def search_by_tag(self, tag: str) -> List[Asset]:
        """Search for assets containing the given tag case-insensitively."""
        tag_norm = tag.strip().lower()
        rows = self.db.query(AssetTag).filter(func.lower(AssetTag.tag) == tag_norm).all()
        asset_ids = [r.asset_id for r in rows]
        if not asset_ids:
            return []
        return self.db.query(Asset).filter(Asset.id.in_(asset_ids)).all()


def extract_tags_from_job(db: Session, job: "GenerationJob", spec: dict) -> List[str]:
    """Deterministically extracts tags from Scene, ShotPlan, CharacterProfile, PromptBundle, RenderProfile."""
    tags = set()

    # 1. Extract from RenderProfile
    render_profile = spec.get("metadata", {}).get("render_profile") or "anime_production"
    if "anime" in render_profile.lower():
        tags.add("anime")

    # 2. Extract from spec compiled positive prompt (which represents the PromptBundle)
    compiled_pos = spec.get("compiled_positive_prompt", job.prompt or "")
    if isinstance(compiled_pos, str):
        pos_lower = compiled_pos.lower()
        
        # Location keywords
        for loc in ["forest", "castle", "ruins", "dungeon", "field", "mountain", "ocean", "desert"]:
            if loc in pos_lower:
                tags.add(loc)
                
        # Mood and theme keywords
        for mood in ["dramatic", "night", "magic", "battle", "dark", "happy", "tense", "mysterious"]:
            if mood in pos_lower:
                tags.add(mood)

        # Camera and composition keywords
        if "close" in pos_lower:
            tags.add("close_up")
        if "wide" in pos_lower:
            tags.add("wide_shot")
        if "medium" in pos_lower:
            tags.add("medium_shot")
        if "rule of thirds" in pos_lower:
            tags.add("rule_of_thirds")
        if "cinematic" in pos_lower:
            tags.add("dramatic")

    # 3. Extract from Scene details
    if job.scene:
        # Title words
        if job.scene.title:
            for word in job.scene.title.lower().split():
                cleaned = "".join(c for c in word if c.isalnum())
                if cleaned in ["forest", "castle", "battle", "night", "magic", "dramatic", "anime"]:
                    tags.add(cleaned)

        # Camera notes
        if job.scene.camera_notes:
            notes_lower = job.scene.camera_notes.lower()
            if "close" in notes_lower:
                tags.add("close_up")
            if "wide" in notes_lower:
                tags.add("wide_shot")
            if "dramatic" in notes_lower:
                tags.add("dramatic")
            if "night" in notes_lower:
                tags.add("night")

        # Characters in scene (Main Character / CharacterProfile)
        if job.scene.characters:
            for char in job.scene.characters:
                tags.add(char.name.lower().strip())
                if char.hair_color:
                    tags.add(char.hair_color.lower().strip())
                if char.eye_color:
                    tags.add(char.eye_color.lower().strip())

    return list(tags)
