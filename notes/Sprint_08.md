# Sprint 08 — Scene Character Mapping

**Date:** 2026-06-29  
**Branch:** `sprint-8-scene-character-mapping` (merged into `main`)  
**Commit Hash:** `8c121b3` (`8c121b37ee520ac46b4a1a67b80e23959afd880a`)

---

## Files Changed

| File | Change Type | Purpose |
|------|-------------|---------|
| `app/models/scene.py` | Modified | Declared `scene_characters` association table and relationship to Character model. |
| `app/models/character.py` | Modified | Imported `scene_characters` and added relationship to Scene model. |
| `app/schemas/scene_character.py` | Created | Pydantic validation schemas (`SceneCharacterAssign` and `SceneCharacterResponse`). |
| `app/services/scene_character.py` | Created | Database service functions (`assign_character_to_scene`, `get_scene_characters`, `get_character_scenes`). |
| `app/api/scene_characters.py` | Created | Router for Scene Character Mapping endpoints. |
| `app/main.py` | Modified | Imported and registered `scene_characters_router`. |
| `alembic/versions/1ac851b183d5_create_scene_characters_table.py` | Created | Database migration script creating the `scene_characters` association table. |
| `notes/Sprint_08.md` | Created | Development journal for Sprint 8. |

---

## Database Changes

### Association Table Design: `scene_characters`

A many-to-many junction table to map scenes to characters.

| Column | Type | Constraints / Default |
|--------|------|-----------------------|
| `scene_id` | INTEGER | ForeignKey("scenes.id"), Primary Key |
| `character_id` | INTEGER | ForeignKey("characters.id"), Primary Key |

- **Primary Key:** Composite Key (`scene_id`, `character_id`)
- **No extra columns** are present.

---

## API Endpoints

- `POST /scenes/{scene_id}/characters/{character_id}`: Assign a character to a scene. Returns 201 Created.
- `GET /scenes/{scene_id}/characters`: Retrieve all characters assigned to a scene. Returns 200 OK.
- `GET /characters/{character_id}/scenes`: Retrieve all scenes a character is assigned to. Returns 200 OK.

---

## Example Requests & Responses

### 1. Assign Character to Scene (`POST /scenes/1/characters/1`)

#### Request
`POST /scenes/1/characters/1` (No request body required)

#### Response (`201 Created`)
```json
{
  "scene_id": 1,
  "character_id": 1
}
```

### 2. Get Scene Characters (`GET /scenes/1/characters`)

#### Request
`GET /scenes/1/characters`

#### Response (`200 OK`)
```json
[
  {
    "id": 1,
    "story_id": 1,
    "name": "Z-100",
    "aliases": "Zee",
    "role": "Protagonist",
    "description": "An awakened humanoid droid.",
    "age": "2 years",
    "gender": "Non-binary",
    "species": "Android",
    "height_cm": 185,
    "body_type": "Slender metallic",
    "hair_color": "None",
    "hair_style": "Bald",
    "eye_color": "Blue LED",
    "skin_tone": "Silver chrome",
    "face_description": "Angular steel plate features.",
    "clothing": "Jumpsuit",
    "accessories": "Utility belt",
    "personality": "Curious and logical",
    "art_style_override": "cyberpunk digital painting",
    "reference_prompt": "A close up portrait of silver android robot with blue eyes.",
    "negative_prompt": "organic skin, hair, human",
    "consistency_notes": "Always keep blue eye LEDs glowing.",
    "status": "draft",
    "created_at": "2026-06-29T16:59:04.140771"
  }
]
```

---

## Lessons Learned

1. **Junction Table references in SQLAlchemy:** Using `secondary=scene_characters` directly is simple when both relationship entities reference it. If declared in `scene.py`, it can be imported in `character.py` without introducing circular imports because relationships use string names for target models (e.g. `"Scene"` and `"Character"`).
2. **Preventing Duplicates in Many-to-Many:** In service layers, querying `if character not in scene.characters` before appending prevents SQLite constraint violations or duplicate rows on connection commit.

---

## Regression Status

All endpoints from Sprints 1-8 are fully verified and passing:
- **Projects:** Creating/listing projects and validation constraints work correctly.
- **Stories:** Story management operations work correctly.
- **Episodes:** Episode hierarchy operations work correctly.
- **Scenes:** Scene listing and details retrieve successfully.
- **Blueprint:** Blueprint compiler works with no regressions.
- **Characters:** Registry creation, listing, and lookups pass.
- **Scene Character Mapping:** Many-to-many assignment, duplicate prevention, and cross-lookup GET endpoints work correctly, including proper 404 responses for non-existent scene or character IDs.
