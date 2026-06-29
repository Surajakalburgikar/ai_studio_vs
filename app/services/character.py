from sqlalchemy.orm import Session

from app.models.character import Character
from app.schemas.character import CharacterCreate


def create_character(db: Session, story_id: int, payload: CharacterCreate) -> Character:
    """Create a new character under the given story."""
    character = Character(
        story_id=story_id,
        name=payload.name,
        aliases=payload.aliases,
        role=payload.role,
        description=payload.description,
        age=payload.age,
        gender=payload.gender,
        species=payload.species,
        height_cm=payload.height_cm,
        body_type=payload.body_type,
        hair_color=payload.hair_color,
        hair_style=payload.hair_style,
        eye_color=payload.eye_color,
        skin_tone=payload.skin_tone,
        face_description=payload.face_description,
        clothing=payload.clothing,
        accessories=payload.accessories,
        personality=payload.personality,
        art_style_override=payload.art_style_override,
        reference_prompt=payload.reference_prompt,
        negative_prompt=payload.negative_prompt,
        consistency_notes=payload.consistency_notes,
    )
    db.add(character)
    db.commit()
    db.refresh(character)
    return character


def get_story_characters(db: Session, story_id: int) -> list[Character]:
    """Return all characters for a story ordered by created_at ascending."""
    return (
        db.query(Character)
        .filter(Character.story_id == story_id)
        .order_by(Character.created_at.asc())
        .all()
    )


def get_character(db: Session, character_id: int) -> Character | None:
    """Return a single character by its ID, or None if not found."""
    return db.query(Character).filter(Character.id == character_id).first()
