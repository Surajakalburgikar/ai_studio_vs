"""
PromptBuilder engine to construct modular PromptBundles from structured planning inputs.
"""

import logging
import os
from typing import List, Dict, Any, Optional

from app.models.project import Project
from app.services.ai.models.scene_direction import SceneDirection
from app.services.ai.models.shot_plan import ShotPlan
from app.services.ai.models.character_profile import CharacterProfile
from app.services.ai.models.prompt_bundle import PromptBundle
from app.services.ai.exceptions import ValidationError

logger = logging.getLogger("ai_studio")

# Default profiles for style, quality, and technical modifiers
PROFILES = {
    "anime": {
        "style_tags": ["anime style", "aesthetic anime", "vibrant colors"],
        "quality_tags": ["masterpiece", "best quality", "highly detailed"],
        "technical_tags": ["sharp focus", "resolution 4k"],
        "default_negative": ["low quality", "worst quality", "blurry", "extra limbs", "bad anatomy"]
    },
    "realistic": {
        "style_tags": ["photorealistic", "hyperrealistic", "realistic lighting"],
        "quality_tags": ["masterpiece", "best quality"],
        "technical_tags": ["dslr", "8k resolution", "sharp focus"],
        "default_negative": ["low quality", "worst quality", "blurry", "3d render", "cartoon", "anime"]
    },
    "cinematic": {
        "style_tags": ["cinematic film still", "35mm photograph", "dramatic framing"],
        "quality_tags": ["masterpiece", "high dynamic range"],
        "technical_tags": ["filmic grain", "depth of field", "anamorphic lens"],
        "default_negative": ["low quality", "worst quality", "blurry", "oversaturated", "amateur"]
    }
}


class PromptBuilder:
    """Builder class that compiles modular PromptBundles using templates and style profiles."""

    def __init__(self, template_dir: Optional[str] = None) -> None:
        if template_dir is None:
            # Locate relative to the app module
            template_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                "prompts"
            )
        self.template_dir = template_dir
        self.pos_template_path = os.path.join(self.template_dir, "positive_prompt_template.txt")
        self.neg_template_path = os.path.join(self.template_dir, "negative_prompt_template.txt")

    def _load_template(self, path: str) -> str:
        """Loads a template file from disk, fallback to a basic placeholder-based template if missing."""
        if not os.path.exists(path):
            raise ValidationError(f"Prompt template file not found at: {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise ValidationError(f"Failed to read prompt template from {path}: {e}")

    def build_prompt_bundle(
        self,
        project: Project,
        scene_direction: SceneDirection,
        shot_plan: ShotPlan,
        character_profiles: List[CharacterProfile]
    ) -> PromptBundle:
        """Constructs a modular PromptBundle from planning objects.

        Args:
            project: Parent Project configuration.
            scene_direction: Directorial guidance for the active scene.
            shot_plan: Framing, movement, and timing details for the shot.
            character_profiles: Profiles of characters participating in this shot.

        Returns:
            Fully populated PromptBundle.
        """
        logger.info("Prompt build started.")

        # 1. Resolve style profile
        art_style = (project.art_style or "anime").lower()
        if art_style not in PROFILES:
            logger.warning(f"Art style '{art_style}' not found. Defaulting to 'anime'.")
            art_style = "anime"
        profile = PROFILES[art_style]

        # 2. Extract camera tags
        camera_tags = []
        if shot_plan.shot_type:
            camera_tags.append(shot_plan.shot_type)
        if shot_plan.camera_angle:
            camera_tags.append(shot_plan.camera_angle)
        if shot_plan.camera_movement:
            camera_tags.append(shot_plan.camera_movement)
        logger.info(f"Camera tags: {camera_tags}")

        # 3. Extract environment and lighting tags
        environment_tags = []
        if scene_direction.mood:
            environment_tags.append(scene_direction.mood)
        if scene_direction.primary_focus:
            environment_tags.append(scene_direction.primary_focus)
        logger.info(f"Environment tags: {environment_tags}")

        lighting_tags = []
        if scene_direction.lighting:
            lighting_tags.append(scene_direction.lighting)
        if shot_plan.visual_notes:
            lighting_tags.append(shot_plan.visual_notes)

        # 4. Extract character tags (DO NOT fabricate traits)
        character_tags = []
        negative_prompt_parts = list(profile["default_negative"])

        for cp in character_profiles:
            char_desc_parts = []
            if cp.reference_prompt:
                char_desc_parts.append(cp.reference_prompt)
            if cp.hair_color:
                char_desc_parts.append(f"{cp.hair_color} hair")
            if cp.hairstyle:
                char_desc_parts.append(cp.hairstyle)
            if cp.eye_color:
                char_desc_parts.append(f"{cp.eye_color} eyes")
            if cp.skin_tone:
                char_desc_parts.append(f"{cp.skin_tone} skin")
            
            # Incorporate active visual continuity states
            cvs = cp.current_visual_state
            if cvs:
                if cvs.outfit:
                    char_desc_parts.append(cvs.outfit)
                elif cp.default_outfit:
                    char_desc_parts.append(cp.default_outfit)
                if cvs.expression:
                    char_desc_parts.append(cvs.expression)
                if cvs.pose:
                    char_desc_parts.append(cvs.pose)
                if cvs.props:
                    char_desc_parts.append(cvs.props)
                if cvs.injuries:
                    char_desc_parts.append(cvs.injuries)
                if cvs.weather_effects:
                    char_desc_parts.append(cvs.weather_effects)
                if cvs.temporary_changes:
                    char_desc_parts.append(cvs.temporary_changes)

            if char_desc_parts:
                character_tags.append(", ".join(char_desc_parts))

            # Character negative prompt integration
            if cp.negative_prompt:
                negative_prompt_parts.append(cp.negative_prompt)

        logger.info(f"Character tags: {character_tags}")

        # 5. Populate positive parts
        positive_parts = []
        if shot_plan.description:
            positive_parts.append(shot_plan.description)

        # 6. Compose the PromptBundle
        bundle = PromptBundle(
            shot_id=f"{shot_plan.scene_id}_{shot_plan.shot_number}",
            positive_prompt_parts=positive_parts,
            negative_prompt_parts=negative_prompt_parts,
            style_tags=list(profile["style_tags"]),
            quality_tags=list(profile["quality_tags"]),
            camera_tags=camera_tags,
            character_tags=character_tags,
            environment_tags=environment_tags,
            lighting_tags=lighting_tags,
            composition_tags=[shot_plan.composition] if shot_plan.composition else [],
            technical_tags=list(profile["technical_tags"])
        )

        # 7. Compile and validate
        self.compile_and_validate(bundle)
        logger.info("Prompt compiled.")

        return bundle

    def compile_and_validate(self, bundle: PromptBundle) -> None:
        """Compiles positive and negative strings using templates and validates results."""
        pos_template = self._load_template(self.pos_template_path)
        neg_template = self._load_template(self.neg_template_path)

        pos_str = self.compile_from_template(pos_template, {
            "positive_prompt_parts": bundle.positive_prompt_parts,
            "style_tags": bundle.style_tags,
            "quality_tags": bundle.quality_tags,
            "camera_tags": bundle.camera_tags,
            "character_tags": bundle.character_tags,
            "environment_tags": bundle.environment_tags,
            "lighting_tags": bundle.lighting_tags,
            "composition_tags": bundle.composition_tags,
            "technical_tags": bundle.technical_tags
        })

        neg_str = self.compile_from_template(neg_template, {
            "negative_prompt_parts": bundle.negative_prompt_parts
        })

        # Validation rules
        if not pos_str.strip():
            raise ValidationError("Compiled positive prompt is empty.")

        # Check for forbidden character constructs
        for word in ["{", "}", "<", ">"]:
            if word in pos_str or word in neg_str:
                raise ValidationError(f"Prompt contains invalid character sequence: {word}")

        # Cache compiled strings inside bundle metadata for reference
        bundle.metadata["compiled_positive"] = pos_str
        bundle.metadata["compiled_negative"] = neg_str

    @staticmethod
    def compile_from_template(template_str: str, placeholders: Dict[str, Any]) -> str:
        """Formats and deduplicates template strings."""
        formatted_placeholders = {}
        for k, v in placeholders.items():
            if isinstance(v, list):
                # Filter empty elements and join
                formatted_placeholders[k] = ", ".join([str(item).strip() for item in v if item and str(item).strip()])
            else:
                formatted_placeholders[k] = str(v).strip() if v is not None else ""

        # Filter comments from template
        lines = [
            line.strip()
            for line in template_str.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]
        clean_template = " ".join(lines)

        try:
            raw_prompt = clean_template.format(**formatted_placeholders)
        except KeyError as e:
            raise ValidationError(f"Template placeholder formatting error: missing variable {e}")

        # Split by comma, normalize spacing, and remove duplicates preserving order
        tags = []
        seen = set()
        for tag in raw_prompt.split(","):
            cleaned = " ".join(tag.split())
            if cleaned and cleaned.lower() not in seen:
                tags.append(cleaned)
                seen.add(cleaned.lower())

        return ", ".join(tags)
