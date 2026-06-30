"""
Story validator to verify parsed story structures against business rules.
"""

import logging
from typing import Dict, Any
from app.services.ai.exceptions import ValidationError

logger = logging.getLogger("ai_studio")


class StoryValidator:
    """Validates the structure, types, and logic of a parsed story dictionary."""

    def validate(self, data: Dict[str, Any]) -> None:
        """Validate the story dictionary structure.

        Args:
            data: Parsed story dictionary.

        Raises:
            ValidationError: If any validation rule is violated.
        """
        # 1. Required story fields
        story_fields = ["title", "genre", "summary", "story_text", "episodes"]
        for f in story_fields:
            if f not in data or data[f] is None:
                raise ValidationError(f"Missing required story field: '{f}'")

        if not isinstance(data["title"], str) or not data["title"].strip():
            raise ValidationError("Story title must be a non-empty string")

        if not isinstance(data["episodes"], list):
            raise ValidationError("Episodes must be a list")

        if not data["episodes"]:
            raise ValidationError("Story must contain at least one episode")

        episode_numbers = set()

        # 2. Validate each episode
        for ep_idx, ep in enumerate(data["episodes"]):
            ep_label = f"Episode at index {ep_idx}"

            # Required episode fields
            ep_fields = ["episode_number", "title", "summary", "scenes"]
            for f in ep_fields:
                if f not in ep or ep[f] is None:
                    raise ValidationError(f"{ep_label} is missing field: '{f}'")

            if not isinstance(ep["episode_number"], int):
                raise ValidationError(f"{ep_label} episode_number must be an integer")

            if ep["episode_number"] in episode_numbers:
                raise ValidationError(f"Duplicate episode number detected: {ep['episode_number']}")
            episode_numbers.add(ep["episode_number"])

            if not isinstance(ep["title"], str) or not ep["title"].strip():
                raise ValidationError(f"{ep_label} title must be a non-empty string")

            if not isinstance(ep["scenes"], list):
                raise ValidationError(f"{ep_label} scenes must be a list")

            if not ep["scenes"]:
                raise ValidationError(f"{ep_label} must contain at least one scene")

            scene_numbers = []

            # 3. Validate each scene inside episode
            for sc_idx, scene in enumerate(ep["scenes"]):
                sc_label = f"Scene at index {sc_idx} under Episode {ep['episode_number']}"

                # Required scene fields
                sc_fields = ["scene_number", "title", "narration", "camera_notes", "duration_seconds"]
                for f in sc_fields:
                    if f not in scene or scene[f] is None:
                        raise ValidationError(f"{sc_label} is missing field: '{f}'")

                if not isinstance(scene["scene_number"], int):
                    raise ValidationError(f"{sc_label} scene_number must be an integer")
                scene_numbers.append(scene["scene_number"])

                if not isinstance(scene["title"], str) or not scene["title"].strip():
                    raise ValidationError(f"{sc_label} title must be a non-empty string")

                # Validate duration
                duration = scene["duration_seconds"]
                if not isinstance(duration, (int, float)):
                    raise ValidationError(f"{sc_label} duration_seconds must be a number")
                if duration <= 0:
                    raise ValidationError(f"{sc_label} duration_seconds must be greater than 0")

            # Validate scene ordering (sequential starting at 1: 1, 2, 3...)
            sorted_scene_numbers = sorted(scene_numbers)
            expected_numbers = list(range(1, len(scene_numbers) + 1))
            if sorted_scene_numbers != expected_numbers:
                raise ValidationError(
                    f"Scenes in Episode {ep['episode_number']} are not in sequential order from 1. "
                    f"Got {scene_numbers}, expected {expected_numbers}."
                )

        logger.info(f"Story validation successful: '{data['title']}' ({len(data['episodes'])} episodes)")
