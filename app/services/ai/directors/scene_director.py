"""
Scene Director Service.

Analyzes scenes to produce high-level cinematic direction guidelines
(Mood, Lighting, Primary Focus, Camera Style, Shot Sequences).
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.services.ai.pipeline_context import PipelineContext
from app.services.ai.directors.shot_types import ShotType
from app.services.ai.directors.camera_language import CameraMovement
from app.services.ai.directors.composition_rules import CompositionRule

logger = logging.getLogger("ai_studio")


class SceneDirector:
    """Orchestrates scene analysis and plans camera styles, lighting, and shots."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def direct_scenes(self, context: PipelineContext) -> PipelineContext:
        """Analyze all scenes in the context and append cinematic directions.

        Args:
            context: Shared PipelineContext containing the generated project scenes.

        Returns:
            Updated PipelineContext with scene direction metadata populated.
        """
        logger.info("Scene analysis started")
        
        # Initialize dictionary if not present
        if "scene_direction" not in context.metadata:
            context.metadata["scene_direction"] = {"scenes": []}

        scenes_directions = context.metadata["scene_direction"]["scenes"]

        for idx, scene in enumerate(context.scenes):
            logger.info(f"Analyzing Scene ID: {scene.id}")
            
            # Generate cinematic direction details
            direction_plan = {
                "scene_id": scene.id,
                "scene_number": scene.scene_number,
                "title": scene.title or f"Scene {scene.scene_number}",
                "direction": {
                    "mood": "Mysterious" if idx % 2 == 0 else "Dramatic",
                    "lighting": "Low-key, high-contrast chiaroscuro" if idx % 2 == 0 else "Warm ambient backlighting",
                    "primary_focus": scene.title or "Primary character interaction",
                    "camera_style": "Slow slow pans and tracking movements",
                    "suggested_shot_sequence": [
                        {
                            "shot_number": 1,
                            "shot_type": ShotType.ESTABLISHING.value,
                            "movement": CameraMovement.STATIC.value,
                            "composition": CompositionRule.RULE_OF_THIRDS.value,
                            "description": f"Establishing wide view showing the setting of '{scene.title}'."
                        },
                        {
                            "shot_number": 2,
                            "shot_type": ShotType.MEDIUM.value,
                            "movement": CameraMovement.PAN.value,
                            "composition": CompositionRule.LEADING_LINES.value,
                            "description": "Medium shot framing character emotions and physical context."
                        },
                        {
                            "shot_type": ShotType.CLOSE_UP.value,
                            "movement": CameraMovement.ZOOM.value,
                            "composition": CompositionRule.CENTER_COMPOSITION.value,
                            "description": "Close-up on primary focus item or facial expression."
                        }
                    ],
                    "visual_notes": "Ensure deep shadows and rich color saturation in post-processing."
                }
            }
            
            scenes_directions.append(direction_plan)
            logger.info(f"Scene analyzed: {scene.id}")

        logger.info("Direction completed")
        return context
