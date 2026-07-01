import hashlib
import json
from typing import Optional
from sqlalchemy.orm import Session
from app.models.generation_job import GenerationJob
from app.models.asset import Asset
from .asset_status import AssetStatus
from .asset_revision import get_next_revision_number, mark_revision_canonical

class AssetRegistry:
    """Core coordinator for asset lifecycle events, registration, and workflows."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def register_asset(self, job: GenerationJob) -> Asset:
        """Register a new asset from a completed GenerationJob."""
        project_id = None
        episode_id = None
        scene_id = job.scene_id
        shot_id = job.shot_number
        continuity_key = None
        
        scene = job.scene
        if scene:
            if scene.episode:
                episode_id = scene.episode.id
                if scene.episode.story:
                    project = scene.episode.story.project
                    if project:
                        project_id = project.id
                        continuity_key = project.continuity_key
                        
        spec = {}
        try:
            spec = json.loads(job.prompt)
        except Exception:
            pass
            
        compiled_pos = spec.get("compiled_positive_prompt", job.prompt)
        compiled_neg = spec.get("compiled_negative_prompt", job.negative_prompt)
        spec_version = spec.get("version", "1.0")
        
        params = spec.get("generation_parameters", {})
        seed = params.get("seed")
        width = params.get("width")
        height = params.get("height")
        
        prompt_hash = hashlib.sha256(compiled_pos.encode("utf-8")).hexdigest() if compiled_pos else None
        
        provider = job.provider or spec.get("provider")
        model = spec.get("model")
        
        revision = get_next_revision_number(self.db, project_id, scene_id, shot_id)
        
        # Collect reproducibility and future hooks parameters (Task 7 & Task 9)
        render_profile_val = spec.get("metadata", {}).get("render_profile")
        if not render_profile_val:
            render_profile_val = "anime_production"

        meta_payload = {
            "generation_parameters": params,
            "render_profile": render_profile_val,
            "output_configuration": spec.get("output_configuration", {}),
            "storage_configuration": spec.get("storage_configuration", {}),
            # Task 9 Future Hooks
            "embeddings": None,
            "quality_score": None,
            "similarity_score": None,
            "character_reference_images": [],
            "background_reference_images": [],
            "face_consistency": None,
            "lora_generation": None,
        }

        # Check if AssetCollection exists, otherwise create it
        from app.models.asset_collection import AssetCollection
        from .asset_collection import AssetCollectionRepository

        collection = self.db.query(AssetCollection).filter(
            AssetCollection.project_id == project_id,
            AssetCollection.scene_id == scene_id,
            AssetCollection.shot_number == shot_id
        ).first()

        if not collection:
            repo = AssetCollectionRepository(self.db)
            collection = repo.create_collection(
                project_id=project_id,
                episode_id=episode_id,
                scene_id=scene_id,
                shot_number=shot_id,
                continuity_key=continuity_key
            )

        asset = Asset(
            continuity_key=continuity_key,
            project_id=project_id,
            episode_id=episode_id,
            scene_id=scene_id,
            shot_id=shot_id,
            generation_job_id=job.id,
            asset_type="image",
            image_path=job.drive_file_id,
            thumbnail_path=None,
            storage_provider="local",
            provider=provider,
            model=model,
            seed=seed,
            width=width,
            height=height,
            file_size=None,
            generation_time=job.generation_time,
            prompt_hash=prompt_hash,
            compiled_positive_prompt=compiled_pos,
            compiled_negative_prompt=compiled_neg,
            generation_spec_version=spec_version,
            revision=revision,
            status=AssetStatus.GENERATED,
            metadata_json=meta_payload,
            collection_id=collection.collection_id
        )
        
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)

        # Extract and save tags automatically (Task 3)
        from .asset_tags import AssetTagManager, extract_tags_from_job
        tag_mgr = AssetTagManager(self.db)
        try:
            extracted_tags = extract_tags_from_job(self.db, job, spec)
            for tag in extracted_tags:
                tag_mgr.add_tag(asset.id, tag)
        except Exception as e:
            print(f"Error during tag extraction: {e}")

        return asset

    def approve_asset(self, asset_id: int) -> Asset:
        """Mark an asset revision as approved (canonical) and archive previous approved ones."""
        return mark_revision_canonical(self.db, asset_id)

    def reject_asset(self, asset_id: int) -> Asset:
        """Mark an asset as rejected."""
        asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise ValueError(f"Asset with id {asset_id} not found")
        asset.status = AssetStatus.REJECTED
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def archive_asset(self, asset_id: int) -> Asset:
        """Archive an asset."""
        asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise ValueError(f"Asset with id {asset_id} not found")
        asset.status = AssetStatus.ARCHIVED
        self.db.commit()
        self.db.refresh(asset)
        return asset
