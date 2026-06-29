import os
import json
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.story import Story
from app.models.episode import Episode
from app.models.scene import Scene


class AssetManager:
    """Asset Manager responsible for organizing and tracking generated scene artifacts."""

    def __init__(self, db: Session, scene_id: int):
        scene = db.query(Scene).filter(Scene.id == scene_id).first()
        if not scene:
            raise ValueError(f"Scene with id {scene_id} not found")

        episode = db.query(Episode).filter(Episode.id == scene.episode_id).first()
        if not episode:
            raise ValueError(f"Episode with id {scene.episode_id} not found")

        story = db.query(Story).filter(Story.id == episode.story_id).first()
        if not story:
            raise ValueError(f"Story with id {episode.story_id} not found")

        project = db.query(Project).filter(Project.id == story.project_id).first()
        if not project:
            raise ValueError(f"Project with id {story.project_id} not found")

        self.scene_id = scene.id
        self.base_dir = os.path.join(
            "generated",
            f"project_{project.id}",
            f"story_{story.id}",
            f"episode_{episode.id}",
            f"scene_{scene.id}",
        )

        self.subdirs = {
            "prompts": "prompts",
            "images": "images",
            "voice": "voice",
            "subtitles": "subtitles",
            "clips": "clips",
        }

        # Create nested directories
        for sdir in self.subdirs.values():
            os.makedirs(os.path.join(self.base_dir, sdir), exist_ok=True)

        self.manifest_path = os.path.join(self.base_dir, "manifest.json")
        self._load_or_create_manifest()

    def _load_or_create_manifest(self) -> None:
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    self.manifest = json.load(f)
            except Exception:
                self.manifest = self._get_default_manifest()
        else:
            self.manifest = self._get_default_manifest()
            self._save_manifest()

    def _get_default_manifest(self) -> dict:
        return {
            "scene_id": self.scene_id,
            "prompts": [],
            "images": [],
            "voice": [],
            "subtitles": [],
            "clips": [],
        }

    def _save_manifest(self) -> None:
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2, ensure_ascii=False)

    def _add_to_manifest(self, key: str, filename: str) -> None:
        if filename not in self.manifest[key]:
            self.manifest[key].append(filename)
            self._save_manifest()

    def save_prompt(self, filename: str, content: str) -> str:
        filepath = os.path.join(self.base_dir, "prompts", filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        self._add_to_manifest("prompts", filename)
        return filepath.replace("\\", "/")

    def save_image(self, filename: str, content: bytes) -> str:
        filepath = os.path.join(self.base_dir, "images", filename)
        with open(filepath, "wb") as f:
            f.write(content)
        self._add_to_manifest("images", filename)
        return filepath.replace("\\", "/")

    def save_voice(self, filename: str, content: bytes) -> str:
        filepath = os.path.join(self.base_dir, "voice", filename)
        with open(filepath, "wb") as f:
            f.write(content)
        self._add_to_manifest("voice", filename)
        return filepath.replace("\\", "/")

    def save_subtitle(self, filename: str, content: str) -> str:
        filepath = os.path.join(self.base_dir, "subtitles", filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        self._add_to_manifest("subtitles", filename)
        return filepath.replace("\\", "/")

    def save_clip(self, filename: str, content: bytes) -> str:
        filepath = os.path.join(self.base_dir, "clips", filename)
        with open(filepath, "wb") as f:
            f.write(content)
        self._add_to_manifest("clips", filename)
        return filepath.replace("\\", "/")

    def get_assets_info(self) -> dict:
        existing_files = []
        for root, _, files in os.walk(self.base_dir):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), self.base_dir)
                rel_path = rel_path.replace("\\", "/")
                existing_files.append(rel_path)
        return {
            "directory": self.base_dir.replace("\\", "/"),
            "existing_files": sorted(existing_files),
            "manifest": self.manifest,
        }
