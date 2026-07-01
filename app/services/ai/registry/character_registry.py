"""
Character Registry Coordinator.
"""

import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.character import Character
from app.services.ai.pipeline.pipeline_context import PipelineContext
from app.services.ai.registry.character_normalizer import CharacterNormalizer
from app.services.ai.registry.character_matcher import CharacterMatcher
from app.services.ai.registry.character_profile_builder import CharacterProfileBuilder

logger = logging.getLogger("ai_studio")


class CharacterRegistry:
    """Manages parsing, normalization, matching, database persistence, and profile creation for story characters."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.normalizer = CharacterNormalizer()
        self.matcher = CharacterMatcher(self.normalizer)
        self.profile_builder = CharacterProfileBuilder(self.normalizer)

    def register_characters(self, context: PipelineContext) -> PipelineContext:
        """Process characters in the current PipelineContext, creating missing records,
        and building indexes/profiles.
        """
        logger.info("Registry started")

        if not context.story:
            logger.warning("No story found in PipelineContext; skipping character registration.")
            logger.info("Registry completed")
            return context

        story_id = context.story.id

        # 1. Retrieve all existing database characters for this story
        existing_characters = (
            self.db.query(Character)
            .filter(Character.story_id == story_id)
            .all()
        )
        logger.info(f"Existing characters found in DB: {len(existing_characters)}")

        # 2. Extract potential character names mentioned in story or scene content
        extracted_names = set()

        if "characters" in context.metadata:
            for item in context.metadata["characters"]:
                if isinstance(item, str):
                    extracted_names.add(item)
                elif isinstance(item, dict) and "name" in item:
                    extracted_names.add(item["name"])

        # Also scan scene narration text for character names if they are already in the DB as aliases or known names.
        for char in existing_characters:
            extracted_names.add(char.name)
            if char.aliases:
                for alias in char.aliases.replace(";", ",").split(","):
                    if alias.strip():
                        extracted_names.add(alias.strip())

        # Clean, normalize, and detect duplicates
        normalized_names = self.normalizer.detect_duplicates(list(extracted_names))
        logger.info(f"Characters discovered and normalized: {len(normalized_names)}")

        # 3. Match names to database or create missing records
        active_characters = []
        for name in normalized_names:
            best_match, score = self.matcher.find_best_match(name, existing_characters)

            if best_match and score >= 0.8:
                logger.info(f"Characters matched: '{name}' matches DB character '{best_match.name}' (score {score})")
                if best_match not in active_characters:
                    active_characters.append(best_match)
            else:
                # Create a new Character database record
                logger.info(f"Characters created: No match for '{name}'. Creating new Character record.")
                new_char = Character(
                    story_id=story_id,
                    name=name,
                    aliases=None,
                    role="supporting",
                    description=f"Auto-registered character: {name}",
                    gender="unknown",
                    status="draft"
                )
                self.db.add(new_char)
                self.db.commit()
                self.db.refresh(new_char)
                active_characters.append(new_char)
                existing_characters.append(new_char)

        # Resolve characters against the continuity manifest if present
        continuity_key = getattr(context.project, "continuity_key", None)
        if continuity_key:
            from app.services.ai.continuity.continuity_manager import ContinuityManager
            from app.services.ai.continuity.continuity_resolver import ContinuityResolver
            manager = ContinuityManager()
            manifest = manager.load_manifest(continuity_key)
            if manifest and manifest.canonical_characters:
                resolver = ContinuityResolver()
                char_dicts = []
                for char in active_characters:
                    char_dicts.append({
                        "name": char.name,
                        "description": char.description,
                        "hair_style": getattr(char, "hair_style", None),
                        "hair_color": getattr(char, "hair_color", None),
                        "eye_color": getattr(char, "eye_color", None),
                        "skin_tone": getattr(char, "skin_tone", None),
                        "body_type": getattr(char, "body_type", None),
                        "age": getattr(char, "age", None),
                        "clothing": getattr(char, "clothing", None),
                        "accessories": getattr(char, "accessories", None),
                        "consistency_notes": getattr(char, "consistency_notes", None),
                        "reference_prompt": getattr(char, "reference_prompt", None),
                        "negative_prompt": getattr(char, "negative_prompt", None),
                    })
                resolved_dicts = resolver.resolve_characters(manifest, char_dicts)
                for i, char in enumerate(active_characters):
                    resolved = resolved_dicts[i]
                    for key, val in resolved.items():
                        if val is not None and hasattr(char, key):
                            setattr(char, key, val)
                    self.db.add(char)
                self.db.commit()

        # 4. Build Profiles and Indexes
        context.characters = active_characters
        context.character_profiles = {}
        context.character_scene_index = {}
        context.character_shot_index = {}

        for char in active_characters:
            # Build profile
            profile = self.profile_builder.build_profile(char, context.scenes, context.shot_plans)
            context.character_profiles[profile.canonical_name] = profile
            logger.info(f"Profiles created: Profile built for '{profile.canonical_name}'")

            # Populating Scene Index
            context.character_scene_index[profile.canonical_name] = profile.scene_history

            # Populating Shot Index
            context.character_shot_index[profile.canonical_name] = profile.shot_history

        logger.info("PipelineContext updated")
        logger.info("Registry completed")
        return context
