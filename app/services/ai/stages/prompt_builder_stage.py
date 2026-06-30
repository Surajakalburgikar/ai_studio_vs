"""
Pipeline Stage for building prompt bundles.
"""

import logging
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.services.ai.pipeline.stage import PipelineStage
from app.services.ai.pipeline.pipeline_context import PipelineContext
from app.services.ai.builders.prompt_builder import PromptBuilder

logger = logging.getLogger("ai_studio")


class PromptBuilderStage(PipelineStage):
    """Pipeline stage that calls the PromptBuilder to compile PromptBundles for all shot plans."""

    def __init__(self, db: Session, template_dir: str = None) -> None:
        self.db = db
        self.builder = PromptBuilder(template_dir=template_dir)

    def run(self, context: PipelineContext) -> PipelineContext:
        stage_name = self.__class__.__name__
        logger.info(f"Stage {stage_name} started.")
        t0 = time.perf_counter()

        context.timestamps[f"{stage_name}_started"] = datetime.now(timezone.utc)

        try:
            # 1. Fetch character profiles from context
            char_profiles = list(context.character_profiles.values())

            # 2. Match each shot plan to its parent scene direction
            #    and generate a prompt bundle.
            prompt_bundles = []

            # Map scene directions by scene_id for lookup
            scene_dir_map = {sd.scene_id: sd for sd in context.scene_directions}

            for shot in context.shot_plans:
                # Find matching scene direction
                sd = scene_dir_map.get(shot.scene_id)
                if not sd:
                    # Fallback or create dummy scene direction
                    from app.services.ai.models.scene_direction import SceneDirection
                    sd = SceneDirection(
                        scene_id=shot.scene_id,
                        mood="Dramatic",
                        lighting="Neutral lighting",
                        primary_focus="Subject",
                        camera_style="Standard",
                        composition_rule="Center",
                        camera_movement="Static",
                        visual_notes="None"
                    )

                # Filter profiles for characters that appear in this shot
                shot_chars = []
                for cp in char_profiles:
                    names_to_match = [cp.canonical_name.lower()] + [a.lower() for a in cp.aliases]
                    text_to_check = f"{shot.focus_subject or ''} {shot.description or ''} {shot.visual_notes or ''}".lower()
                    if any(name in text_to_check for name in names_to_match):
                        shot_chars.append(cp)

                bundle = self.builder.build_prompt_bundle(
                    project=context.project,
                    scene_direction=sd,
                    shot_plan=shot,
                    character_profiles=shot_chars
                )
                prompt_bundles.append(bundle)

            # Store in context metadata
            context.metadata["prompt_bundles"] = prompt_bundles
            logger.info(f"Stage {stage_name} succeeded. Created {len(prompt_bundles)} prompt bundles.")

        except Exception as e:
            logger.error(f"Stage {stage_name} failed: {e}")
            context.errors.append(f"{stage_name} failed: {str(e)}")
            context.status = "failed"
            raise e
        finally:
            duration = time.perf_counter() - t0
            context.timestamps[f"{stage_name}_completed"] = datetime.now(timezone.utc)
            logger.info(f"Stage {stage_name} completed in {duration:.4f} seconds.")

        return context
