"""
Shot Planner Service.
"""

import logging
from typing import List
from app.services.ai.models.scene_direction import SceneDirection
from app.services.ai.models.shot_direction import ShotDirection
from app.services.ai.models.shot_plan import ShotPlan

logger = logging.getLogger("ai_studio")


class ShotPlanner:
    """Performs deterministic visual shot planning from scene direction constraints."""

    def plan_shots(self, scene_directions: List[SceneDirection]) -> List[ShotPlan]:
        """Convert a list of SceneDirection objects into concrete ShotPlan objects.

        Args:
            scene_directions: List of input SceneDirection models.

        Returns:
            List of generated ShotPlan models.
        """
        logger.info("Planning started")
        all_shot_plans: List[ShotPlan] = []

        for sd in scene_directions:
            logger.info(f"Scene processed: {sd.scene_id}")

            # 1. Determine target number of shots based on scene duration
            est_duration = sd.estimated_duration if sd.estimated_duration > 0 else 12.0

            if est_duration <= 10.0:
                # Short scene: 1-2 shots
                target_shot_count = min(max(len(sd.suggested_shots), 1), 2)
            elif est_duration <= 20.0:
                # Medium scene: 3-5 shots
                target_shot_count = min(max(len(sd.suggested_shots), 3), 5)
            else:
                # Long scene: 5-8 shots
                target_shot_count = min(max(len(sd.suggested_shots), 5), 8)

            # 2. Build or adjust shots to match target count
            planned_shots: List[ShotPlan] = []

            # Start with existing suggested shots or default descriptions
            shots_to_process = list(sd.suggested_shots)

            # If no suggested shots, create dummy ones
            if not shots_to_process:
                # Fallback list
                shots_to_process = [
                    ShotDirection(
                        shot_number=1,
                        shot_type="Wide Shot",
                        camera_angle="Eye Level",
                        camera_movement="Static",
                        composition="Rule of Thirds",
                        duration_seconds=est_duration,
                        focus_subject="Scene Setting",
                        description="Default fallback wide shot."
                    )
                ]

            # Adjust/clamp to target count
            while len(shots_to_process) < target_shot_count:
                # Duplicate last shot and increment number
                last_shot = shots_to_process[-1]
                new_shot = ShotDirection(
                    shot_number=len(shots_to_process) + 1,
                    shot_type=last_shot.shot_type,
                    camera_angle=last_shot.camera_angle,
                    camera_movement=last_shot.camera_movement,
                    composition=last_shot.composition,
                    duration_seconds=last_shot.duration_seconds,
                    focus_subject=last_shot.focus_subject,
                    description=f"{last_shot.description} (Continued)",
                    notes=last_shot.notes
                )
                shots_to_process.append(new_shot)

            if len(shots_to_process) > target_shot_count:
                shots_to_process = shots_to_process[:target_shot_count]

            # 3. Apply Planning Rules

            # Rule A: Wide shot first
            if shots_to_process:
                first_shot = shots_to_process[0]
                if "Wide" not in first_shot.shot_type and "Establishing" not in first_shot.shot_type:
                    # Modify to be a Wide Shot/Establishing shot
                    first_shot.shot_type = "Establishing"
                    first_shot.description = f"[Wide Establishing Shot] {first_shot.description}"

            # Rule B: Close-up near emotional moments
            is_emotional = sd.mood.lower() in ["dramatic", "mysterious", "tense", "emotional", "joy", "anger"]
            if is_emotional and len(shots_to_process) >= 2:
                # Set one of the middle/later shots to close-up
                close_up_idx = len(shots_to_process) - 1  # near end of scene
                shots_to_process[close_up_idx].shot_type = "Close-up"
                shots_to_process[close_up_idx].description = f"[Close-up emotion shot] {shots_to_process[close_up_idx].description}"
                shots_to_process[close_up_idx].focus_subject = "Character expression"

            # Rule C: Respect SceneDirection camera style and estimated duration
            # Distribute duration evenly across planned shots to total est_duration
            duration_per_shot = round(est_duration / len(shots_to_process), 2)

            for i, shot in enumerate(shots_to_process):
                shot_num = i + 1

                # Rule D: Set transitions
                t_in = "Fade In" if shot_num == 1 else "Cut"
                t_out = "Fade Out" if shot_num == len(shots_to_process) else "Cut"

                plan = ShotPlan(
                    scene_id=sd.scene_id,
                    shot_number=shot_num,
                    shot_type=shot.shot_type,
                    camera_angle=shot.camera_angle,
                    camera_movement=shot.camera_movement,
                    composition=shot.composition,
                    focus_subject=shot.focus_subject,
                    duration_seconds=duration_per_shot,
                    transition_in=t_in,
                    transition_out=t_out,
                    description=shot.description,
                    visual_notes=f"Camera Style: {sd.camera_style}. {sd.visual_notes}",
                    scene_direction_id=None,
                    metadata={"original_notes": shot.notes}
                )
                planned_shots.append(plan)

            logger.info(f"Shots created: {len(planned_shots)} for Scene ID: {sd.scene_id}")
            all_shot_plans.extend(planned_shots)

        logger.info("Pipeline updated")
        return all_shot_plans
