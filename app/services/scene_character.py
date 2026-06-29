from sqlalchemy.orm import Session

from app.models.character import Character
from app.models.scene import Scene


def assign_character_to_scene(
    db: Session, scene_id: int, character_id: int
) -> dict | None:
    """Assign a character to a scene.

    Checks existence of both entities and prevents duplicates.
    """
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    character = db.query(Character).filter(Character.id == character_id).first()

    if scene is None or character is None:
        return None

    if character not in scene.characters:
        scene.characters.append(character)
        db.commit()

    return {"scene_id": scene_id, "character_id": character_id}


def get_scene_characters(db: Session, scene_id: int) -> list[Character] | None:
    """Return all characters assigned to a scene."""
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if scene is None:
        return None
    return scene.characters


def get_character_scenes(db: Session, character_id: int) -> list[Scene] | None:
    """Return all scenes a character is assigned to."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if character is None:
        return None
    return character.scenes
