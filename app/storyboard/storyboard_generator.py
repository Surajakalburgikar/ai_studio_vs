from sqlalchemy.orm import Session

from app.models.character import Character
from app.models.episode import Episode
from app.models.project import Project
from app.models.scene import Scene
from app.models.story import Story


def _val(enum_or_str) -> str:
    """Safely extract string value from an Enum or string."""
    if hasattr(enum_or_str, "value"):
        return str(enum_or_str.value)
    return str(enum_or_str)


def generate_storyboard(db: Session, scene_id: int) -> dict | None:
    """Generate a storyboard dynamically for a given scene using deterministic rules."""
    # 1. Fetch Scene
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if scene is None:
        return None

    # 2. Fetch Episode
    episode = db.query(Episode).filter(Episode.id == scene.episode_id).first()
    if episode is None:
        return None

    # 3. Fetch Story
    story = db.query(Story).filter(Story.id == episode.story_id).first()
    if story is None:
        return None

    # 4. Fetch Project
    project = db.query(Project).filter(Project.id == story.project_id).first()
    if project is None:
        return None

    # 5. Extract scene duration and characters
    scene_duration = scene.duration_seconds
    if scene_duration is None or scene_duration <= 0:
        scene_duration = 10.0

    char_names = [c.name for c in scene.characters]

    # 6. Determine number of shots
    if char_names:
        num_shots = max(3, len(char_names) + 1)
    else:
        num_shots = 3

    duration_per_shot = round(scene_duration / num_shots, 2)

    # 7. Generate shots list
    shots = []
    for i in range(1, num_shots + 1):
        # Shot type & Camera angle
        if i == 1:
            shot_type = "Wide"
            camera_angle = "High Angle"
        elif i == num_shots:
            shot_type = "Close-up"
            camera_angle = "Low Angle"
        else:
            shot_type = "Medium"
            camera_angle = "Eye Level"

        # Focus characters
        if not char_names:
            focus_characters = []
        elif i == 1:
            focus_characters = char_names
        elif i == num_shots:
            focus_characters = [char_names[0]]
        else:
            focus_characters = [char_names[(i - 2) % len(char_names)]]

        # Transition
        transition = "Fade Out" if i == num_shots else "Cut"

        # Description builder
        desc_parts = [
            f"In {_val(project.art_style)} style, framed in {_val(project.aspect_ratio)} aspect ratio."
        ]

        if i == 1:
            desc_parts.append(
                f"An establishing wide shot of the scene '{scene.title}'."
            )
        elif i == num_shots:
            focus_str = f"focusing on {char_names[0]}" if char_names else "focusing on the environment"
            desc_parts.append(f"A detailed close-up shot {focus_str}.")
        else:
            if char_names:
                focus_char = char_names[(i - 2) % len(char_names)]
                desc_parts.append(f"A medium shot focusing on {focus_char}.")
            else:
                desc_parts.append("A medium shot focusing on the details.")

        if scene.narration:
            desc_parts.append(f"Narration: '{scene.narration}'.")

        desc_parts.append(
            f"Audio voicing configured in {project.language} ({_val(project.voice_gender)})."
        )

        description = " ".join(desc_parts)

        shots.append(
            {
                "shot_number": i,
                "shot_type": shot_type,
                "camera_angle": camera_angle,
                "duration_seconds": duration_per_shot,
                "focus_characters": focus_characters,
                "description": description,
                "transition": transition,
            }
        )

    return {
        "scene_id": scene.id,
        "scene_title": scene.title,
        "project_id": project.id,
        "project_title": project.title,
        "shots": shots,
    }
