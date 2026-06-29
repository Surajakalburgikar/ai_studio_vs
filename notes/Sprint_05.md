# Sprint 05 — Project Configuration

**Date:** 2026-06-29  
**Branch:** `sprint-5-project-configuration` (merged into `main`)  
**Commit Hash:** `f3d8780` (`f3d8780ded97fa097d9ef8e633c319104abb5870`)

---

## Files Changed

| File | Change Type | Change Description |
|------|-------------|--------------------|
| `app/models/project.py` | Modified | Added python `Enum` classes (`VideoType`, `AspectRatio`, `ArtStyle`, `NarrationStyle`, `VoiceGender`) and added new configuration fields to `Project` model mapping using `SQLEnum` with `values_callable`. |
| `app/schemas/project.py` | Modified | Updated `ProjectCreate` and `ProjectResponse` schemas to include new configuration fields and enum-based validations. |
| `app/services/project.py` | Modified | Updated `create_project` function to explicitly map the new configuration payload fields to the `Project` model during instantiation. |
| `alembic/versions/c82a0b2292de_add_project_configuration_fields.py` | Created | Database migration script adding the configuration columns with SQLite-compatible `server_default` values. |
| `notes/Sprint_05.md` | Created | This development journal / sprint report. |

---

## Database Changes

The `projects` table was altered to add the following columns:

| Column | Type | Constraints / Default |
|--------|------|-----------------------|
| `video_type` | VARCHAR | NOT NULL, server_default='medium' |
| `target_duration_seconds` | INTEGER | NOT NULL, server_default='180' |
| `aspect_ratio` | VARCHAR | NOT NULL, server_default='16:9' |
| `language` | VARCHAR(100) | NOT NULL, server_default='English' |
| `art_style` | VARCHAR | NOT NULL, server_default='anime' |
| `narration_style` | VARCHAR | NOT NULL, server_default='third_person' |
| `subtitle_language` | VARCHAR(100) | NOT NULL, server_default='English' |
| `voice_gender` | VARCHAR | NOT NULL, server_default='male' |

---

## Migration

- **Migration Revision ID:** `c82a0b2292de`
- **Revises:** `164be27a3631` (Sprint 4: Scenes)
- **Path:** `alembic/versions/c82a0b2292de_add_project_configuration_fields.py`

*Note: The migration script was modified to include SQLite-compatible defaults (`server_default`) to handle pre-existing data in the sqlite database successfully.*

---

## Validation Rules

Validation constraints are enforced at the API boundaries via Pydantic model configurations:
1. **video_type**: Acceptable values are `short`, `medium`, `long`, `series` (enforced via python `VideoType` enum).
2. **aspect_ratio**: Acceptable values are `9:16`, `16:9`, `1:1` (enforced via python `AspectRatio` enum).
3. **art_style**: Acceptable values are `anime`, `manhwa`, `manga`, `semi_realistic` (enforced via python `ArtStyle` enum).
4. **narration_style**: Acceptable values are `third_person`, `first_person` (enforced via python `NarrationStyle` enum).
5. **voice_gender**: Acceptable values are `male`, `female` (enforced via python `VoiceGender` enum).
6. **target_duration_seconds**: Must be strictly greater than 0 (`gt=0` validation on Pydantic field).

Invalid values trigger a standard FastAPI `422 Unprocessable Entity` HTTP response.

---

## Example Request & Response

### Example Request (`POST /projects`)

```json
{
  "title": "Custom Config Project",
  "description": "Checking custom configurations",
  "video_type": "short",
  "target_duration_seconds": 60,
  "aspect_ratio": "9:16",
  "language": "Spanish",
  "art_style": "manhwa",
  "narration_style": "first_person",
  "subtitle_language": "Spanish",
  "voice_gender": "female"
}
```

### Example Response (`201 Created`)

```json
{
  "id": 7,
  "title": "Custom Config Project",
  "description": "Checking custom configurations",
  "status": "draft",
  "created_at": "2026-06-29T10:22:56.551323",
  "video_type": "short",
  "target_duration_seconds": 60,
  "aspect_ratio": "9:16",
  "language": "Spanish",
  "art_style": "manhwa",
  "narration_style": "first_person",
  "subtitle_language": "Spanish",
  "voice_gender": "female"
}
```

---

## Architecture Impact

- **Enum-Based Type Enforcement:** Introduced type safety at the schema boundary and the ORM layer using python standard Enums.
- **SQLite DDL Compatibility:** Added explicit `values_callable` mapping and manual `server_default` configurations on migrations to ensure SQLite can safely alter columns on tables containing pre-existing rows without failures.
- **Unified Endpoints:** Configured fields to be optional and defaults automatically generated so that existing code and consumers using the legacy payload can continue to use `/projects` seamlessly without changes.

---

## Lessons Learned

1. **SQLite Alter Constraints:** SQLite doesn't natively allow adding `NOT NULL` columns without a default value to pre-existing tables. Using `server_default` inside Alembic migration is critical for database robustness when migrating stateful production/development environments.
2. **SQLAlchemy Enum values vs keys:** Subclassing `str` and `Enum` allows Pydantic to validate input strings naturally, but SQLAlchemy's `Enum` default behavior maps the enum *name* (e.g. `NINE_TO_SIXTEEN`) rather than its *value* (e.g. `9:16`). Adding `values_callable=lambda x: [e.value for e in x]` solves this mismatch elegantly by mapping lowercase string values directly to/from the database rows.

---

## Regression Status

- **Projects:** Creating/listing projects works successfully and returns new configuration schemas.
- **Stories:** Creating stories under projects works successfully.
- **Episodes:** Creating episodes under stories works successfully.
- **Scenes:** Creating scenes under episodes works successfully.
- All previous sprint requirements are intact, fully compatible, and verified.
