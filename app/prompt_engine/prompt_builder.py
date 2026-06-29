from sqlalchemy.orm import Session

from app.models.character import Character
from app.models.episode import Episode
from app.models.project import Project
from app.models.scene import Scene
from app.models.story import Story
from app.storyboard.storyboard_generator import _val, generate_storyboard


def _build_character_appearance(char: Character) -> str:
    """Construct a detailed descriptive string of a character's appearance and role."""
    parts = [f"{char.name} ({char.role})"]
    parts.append(f"gender: {char.gender}")
    if char.age:
        parts.append(f"age: {char.age}")
    if char.species:
        parts.append(f"species: {char.species}")
    if char.body_type:
        parts.append(f"body: {char.body_type}")
    
    hair_desc = " ".join(filter(None, [char.hair_style, char.hair_color]))
    if hair_desc:
        parts.append(f"hair: {hair_desc}")
    if char.eye_color:
        parts.append(f"eyes: {char.eye_color}")
    if char.skin_tone:
        parts.append(f"skin: {char.skin_tone}")
    if char.face_description:
        parts.append(f"face: {char.face_description}")
    if char.clothing:
        parts.append(f"clothing: {char.clothing}")
    if char.accessories:
        parts.append(f"accessories: {char.accessories}")
    if char.personality:
        parts.append(f"personality: {char.personality}")
    if char.reference_prompt:
        parts.append(f"reference: {char.reference_prompt}")
    if char.consistency_notes:
        parts.append(f"notes: {char.consistency_notes}")
    
    return ", ".join(parts)


def build_prompts(db: Session, scene_id: int) -> dict | None:
    """Generate production-ready positive and negative prompts for each storyboard shot."""
    # 1. Fetch storyboard (automatically validates scene existence)
    storyboard = generate_storyboard(db, scene_id)
    if storyboard is None:
        return None

    # 2. Fetch parent entities
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    episode = db.query(Episode).filter(Episode.id == scene.episode_id).first()
    story = db.query(Story).filter(Story.id == episode.story_id).first()
    project = db.query(Project).filter(Project.id == story.project_id).first()

    # Match character names to character objects
    char_map = {c.name: c for c in scene.characters}

    # 3. Process each shot
    prompt_shots = []
    for shot in storyboard["shots"]:
        shot_number = shot["shot_number"]

        # positive prompt elements
        pos_parts = [
            f"{_val(project.art_style)} style",
            f"aspect ratio {_val(project.aspect_ratio)}",
            f"{shot['camera_angle']}",
            f"{shot['shot_type']} shot",
            f"environment: {scene.title}",
        ]

        if scene.camera_notes:
            pos_parts.append(f"camera notes: {scene.camera_notes}")
        if scene.narration:
            pos_parts.append(f"narration: {scene.narration}")

        for name in shot["focus_characters"]:
            if name in char_map:
                pos_parts.append(_build_character_appearance(char_map[name]))
            else:
                pos_parts.append(f"character: {name}")

        pos_parts.append("cinematic lighting, high detail, masterpiece")
        positive_prompt = ", ".join(pos_parts)

        # negative prompt elements
        neg_parts = [
            "low quality, blurry, worst quality, normal quality",  # project defaults
        ]
        for name in shot["focus_characters"]:
            if name in char_map and char_map[name].negative_prompt:
                neg_parts.append(char_map[name].negative_prompt)

        neg_parts.append(
            "extra limbs, bad anatomy, deformed, mutated, disfigured, watermark, text, logo, signature"  # common negatives
        )
        negative_prompt = ", ".join(neg_parts)

        # filename suggestion
        image_filename = f"scene_{scene.scene_number:03d}_shot_{shot_number:03d}.png"

        prompt_shots.append(
            {
                "shot_number": shot_number,
                "positive_prompt": positive_prompt,
                "negative_prompt": negative_prompt,
                "image_filename": image_filename,
            }
        )

    return {
        "scene_id": scene.id,
        "scene_title": scene.title,
        "project_id": project.id,
        "project_title": project.title,
        "shots": prompt_shots,
    }
