# Sprint 07 — Character Registry

**Date:** 2026-06-29  
**Branch:** `sprint-7-character-registry` (merged into `main`)  
**Commit Hash:** `d83dca5` (`d83dca59e4fd4957d3d73d1808738fa41bc1bb48`)

---

## Files Changed

| File | Change Type | Purpose |
|------|-------------|---------|
| `app/models/character.py` | Created | SQLAlchemy model for characters table. |
| `app/models/story.py` | Modified | Declared many-to-one relationship with Character model. |
| `app/models/__init__.py` | Modified | Registered Character model on Base. |
| `app/schemas/character.py` | Created | Pydantic validation schemas (`CharacterCreate` and `CharacterResponse`). |
| `app/services/character.py` | Created | Database service functions (`create_character`, `get_story_characters`, `get_character`). |
| `app/api/characters.py` | Created | Router for Character registry endpoints. |
| `app/main.py` | Modified | Imported and registered `characters_router`. |
| `alembic/versions/5f968d35998d_create_characters_table.py` | Created | Database migration script creating the `characters` table with foreign key and index constraints. |
| `notes/Sprint_07.md` | Created | Development journal for Sprint 7. |

---

## Database Changes

### New Table: `characters`

| Column | Type | Constraints / Default |
|--------|------|-----------------------|
| `id` | INTEGER | Primary Key, Indexed |
| `story_id` | INTEGER | ForeignKey("stories.id"), NOT NULL |
| `name` | VARCHAR(255) | NOT NULL |
| `aliases` | VARCHAR(255) | Nullable |
| `role` | VARCHAR(100) | NOT NULL |
| `description` | TEXT | Nullable |
| `age` | VARCHAR(100) | Nullable |
| `gender` | VARCHAR(100) | NOT NULL |
| `species` | VARCHAR(100) | Nullable |
| `height_cm` | INTEGER | Nullable |
| `body_type` | VARCHAR(100) | Nullable |
| `hair_color` | VARCHAR(100) | Nullable |
| `hair_style` | VARCHAR(100) | Nullable |
| `eye_color` | VARCHAR(100) | Nullable |
| `skin_tone` | VARCHAR(100) | Nullable |
| `face_description` | TEXT | Nullable |
| `clothing` | TEXT | Nullable |
| `accessories` | TEXT | Nullable |
| `personality` | TEXT | Nullable |
| `art_style_override` | TEXT | Nullable |
| `reference_prompt` | TEXT | Nullable |
| `negative_prompt` | TEXT | Nullable |
| `consistency_notes` | TEXT | Nullable |
| `status` | VARCHAR(50) | NOT NULL, default='draft' |
| `created_at` | DateTime(tz) | NOT NULL, server_default=CURRENT_TIMESTAMP |

---

## Migration

- **Migration Revision ID:** `5f968d35998d`
- **Revises:** `c82a0b2292de` (Sprint 5: Project Configuration)
- **Path:** `alembic/versions/5f968d35998d_create_characters_table.py`

---

## Example Request & Response

### Example Request (`POST /stories/{story_id}/characters`)

```json
{
  "name": "Z-100",
  "role": "Protagonist",
  "gender": "Non-binary",
  "aliases": "Zee",
  "description": "An awakened humanoid droid.",
  "age": "2 years",
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
  "consistency_notes": "Always keep blue eye LEDs glowing."
}
```

### Example Response (`201 Created`)

```json
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
```

---

## Architecture Impact

- **Decoupled Character Registration:** Handled separately from Scene mapping in this phase, allowing character details to be stored, queried, and updated prior to layout construction.
- **Robust Field Metadata:** Support for granular visual description fields (body type, hair style/color, clothing, art style overrides, prompts) to provide rich prompts to future down-stream generators.
- **Consistent Session Management:** Direct re-use of database dependency inject patterns without modification to legacy layers.

---

## Lessons Learned

1. **Module shadowing in Python tests:** Avoid importing subpackages (e.g. `import app.models`) when you have imported individual components (e.g. `from app.main import app`) to prevent naming conflicts/shadowing.
2. **SQLite connection isolation:** SQLite's `:memory:` databases are connection-isolated. When testing code that spawns multiple connection cycles, use a temporary file database like `test_temp.db` and delete it during teardown to avoid "no such table" errors.

---

## Regression Status

All endpoints from Sprints 1-7 are verified and passing:
- **Projects:** Creating/listing projects works successfully.
- **Stories:** Creating stories under projects works successfully.
- **Episodes:** Creating episodes under stories works successfully.
- **Scenes:** Creating scenes under episodes works successfully.
- **Blueprint:** Story blueprint compilation and calculation functions work correctly.
- **Characters:** Registry creation, list retrieval, and individual lookups work correctly.
- **Project Config:** Validation for ASPECT_RATIO, VIDEO_TYPE, and duration constraints works correctly.
