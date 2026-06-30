"""
Scene Director Service.

Analyzes scenes to produce high-level cinematic direction guidelines
(Mood, Lighting, Primary Focus, Camera Style, Shot Sequences).
"""

import logging
from typing import List
from sqlalchemy.orm import Session

from app.services.ai.pipeline.pipeline_context import PipelineContext
from app.services.ai.directors.shot_types import ShotType
from app.services.ai.directors.camera_language import CameraMovement
from app.services.ai.directors.composition_rules import CompositionRule
from app.services.ai.models.scene_direction import SceneDirection
from app.services.ai.models.shot_direction import ShotDirection

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
            Updated PipelineContext with scene direction metadata and model list populated.
        """
        logger.info("Scene analysis started")

        # Populate backward compatibility metadata if dictionary not present
        if "scene_direction" not in context.metadata:
            context.metadata["scene_direction"] = {"scenes": []}

        scenes_directions_compat = context.metadata["scene_direction"]["scenes"]

        for idx, scene in enumerate(context.scenes):
            logger.info(f"Analyzing Scene ID: {scene.id}")

            # 1. Build ShotDirection models
            shot1 = ShotDirection(
                shot_number=1,
                shot_type=ShotType.ESTABLISHING.value,
                camera_angle="Eye Level",
                camera_movement=CameraMovement.STATIC.value,
                composition=CompositionRule.RULE_OF_THIRDS.value,
                duration_seconds=5.0,
                focus_subject="Environment setting",
                description=f"Establishing wide view showing the setting of '{scene.title}'."
            )

            shot2 = ShotDirection(
                shot_number=2,
                shot_type=ShotType.MEDIUM.value,
                camera_angle="Eye Level",
                camera_movement=CameraMovement.PAN.value,
                composition=CompositionRule.LEADING_LINES.value,
                duration_seconds=4.0,
                focus_subject="Character context",
                description="Medium shot framing character emotions and physical context."
            )

            shot3 = ShotDirection(
                shot_number=3,
                shot_type=ShotType.CLOSE_UP.value,
                camera_angle="Close Up",
                camera_movement=CameraMovement.ZOOM.value,
                composition=CompositionRule.CENTER_COMPOSITION.value,
                duration_seconds=3.0,
                focus_subject="Primary subject",
                description="Close-up on primary focus item or facial expression."
            )

            suggested_shots = [shot1, shot2, shot3]
            logger.info(f"ShotDirection count: {len(suggested_shots)} for Scene ID: {scene.id}")

            # 2. Build SceneDirection model
            scene_dir = SceneDirection(
                scene_id=scene.id,
                mood="Mysterious" if idx % 2 == 0 else "Dramatic",
                lighting="Low-key, high-contrast chiaroscuro" if idx % 2 == 0 else "Warm ambient backlighting",
                primary_focus=scene.title or "Primary character interaction",
                camera_style="Slow slow pans and tracking movements",
                composition_rule=CompositionRule.RULE_OF_THIRDS.value if idx % 2 == 0 else CompositionRule.LEADING_LINES.value,
                camera_movement=CameraMovement.STATIC.value if idx % 2 == 0 else CameraMovement.PAN.value,
                visual_notes="Ensure deep shadows and rich color saturation in post-processing.",
                suggested_shots=suggested_shots,
                estimated_duration=sum(s.duration_seconds for s in suggested_shots)
            )

            context.scene_directions.append(scene_dir)
            logger.info(f"SceneDirection created: {scene.id}")

            # 3. Add backward compatibility JSON dictionary
            direction_plan_compat = {
                "scene_id": scene.id,
                "scene_number": scene.scene_number,
                "title": scene.title or f"Scene {scene.scene_number}",
                "direction": {
                    "mood": scene_dir.mood,
                    "lighting": scene_dir.lighting,
                    "primary_focus": scene_dir.primary_focus,
                    "camera_style": scene_dir.camera_style,
                    "suggested_shot_sequence": [
                        {
                            "shot_number": s.shot_number,
                            "shot_type": s.shot_type,
                            "movement": s.camera_movement,
                            "composition": s.composition,
                            "description": s.description
                        } for s in suggested_shots
                    ],
                    "visual_notes": scene_dir.visual_notes
                }
            }
            scenes_directions_compat.append(direction_plan_compat)
            logger.info(f"Scene completed: {scene.id}")

        logger.info("PipelineContext updated")
        logger.info("Direction completed")
        return context
