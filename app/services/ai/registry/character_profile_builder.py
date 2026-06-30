"""
Character Profile Builder.
"""

from typing import List, Set, Any
from app.models.character import Character
from app.services.ai.models.character_profile import CharacterProfile, CharacterVisualState
from app.services.ai.models.shot_plan import ShotPlan
from app.services.ai.registry.character_normalizer import CharacterNormalizer


class CharacterProfileBuilder:
    """Aggregates story and shot data to build canonical CharacterProfile runtimes."""

    def __init__(self, normalizer: CharacterNormalizer) -> None:
        self.normalizer = normalizer

    def build_profile(
        self,
        character: Character,
        scenes: List[Any],
        shot_plans: List[ShotPlan]
    ) -> CharacterProfile:
        """Create a complete runtime CharacterProfile for a character.

        Args:
            character: Database Character model.
            scenes: List of Scene objects in the pipeline.
            shot_plans: List of planned ShotPlans in the pipeline.

        Returns:
            Instantiated CharacterProfile.
        """
        canonical_name = self.normalizer.resolve_canonical(character.name)

        # Determine aliases
        aliases_list = []
        if character.aliases:
            aliases_list = [
                self.normalizer.resolve_canonical(a)
                for a in character.aliases.replace(";", ",").split(",")
                if a.strip()
            ]

        # Scan scene history
        scene_ids: Set[int] = set()

        # Check database relationships first
        if character.scenes:
            for s in character.scenes:
                scene_ids.add(s.id)

        # Text-based matching fallbacks for all scenes
        match_names = [canonical_name.lower()] + [a.lower() for a in aliases_list]
        for s in scenes:
            narration_val = getattr(s, "narration", "") or getattr(s, "narration_text", "") or ""
            text_to_check = f"{s.title or ''} {narration_val}".lower()
            if any(name in text_to_check for name in match_names):
                scene_ids.add(s.id)

        # Scan shot history
        shot_ids: List[int] = []
        for plan in shot_plans:
            # Check shot text elements
            text_to_check = f"{plan.focus_subject or ''} {plan.description or ''} {plan.visual_notes or ''}".lower()
            if any(name in text_to_check for name in match_names):
                shot_ids.append(plan.shot_number)

        # Compile profiles mapping directly from database character record
        profile = CharacterProfile(
            character_id=character.id,
            canonical_name=canonical_name,
            aliases=aliases_list,
            appearance_summary=character.description,
            hairstyle=character.hair_style,
            hair_color=character.hair_color,
            eye_color=character.eye_color,
            skin_tone=character.skin_tone,
            body_type=character.body_type,
            age_group=character.age,
            default_outfit=character.clothing,
            accessories=character.accessories,
            expression_defaults=None,  # Not in database, set to None as per guidelines
            pose_defaults=None,
            visual_notes=character.consistency_notes,
            reference_prompt=character.reference_prompt,
            negative_prompt=character.negative_prompt,
            scene_history=sorted(list(scene_ids)),
            shot_history=shot_ids,
            current_visual_state=CharacterVisualState(),
            metadata={"status": character.status, "role": character.role}
        )
        return profile
