# Sprint 04 — Scene Management

**Date:** 2026-06-29  
**Branch:** `sprint-1-project-management` → merged into `main`  
**Commit:** `44a57fd` (`44a57fd5b3a1468024f4052f726a9cadf7fbe48c`)

---

## What We Built

Added Scene Management, the fourth and deepest layer in the hierarchy:

**Project → Story → Episode → Scene**

---

## Files Created

| File | Purpose |
|------|---------|
| `app/models/scene.py` | SQLAlchemy model — `scenes` table with FK to `episodes.id`, `scene_number`, `title`, `narration`, `camera_notes`, `duration_seconds`, `status` (default `"draft"`), `created_at` |
| `app/schemas/scene.py` | Pydantic schemas — `SceneCreate` and `SceneResponse` |
| `app/services/scene.py` | Service layer — `create_scene`, `get_episode_scenes`, `get_scene_by_id` |
| `app/api/scenes.py` | API router — 3 endpoints under `[Scenes]` tag |
| `alembic/versions/164be27a3631_create_scenes_table.py` | Migration — `CREATE TABLE scenes` with FK, index |
| `notes/Sprint_04.md` | This sprint report |

## Files Modified

| File | Change | Lines Changed |
|------|--------|---------------|
| `app/models/episode.py` | Added `scenes = relationship("Scene", back_populates="episode")` | +1 |
| `app/models/__init__.py` | Added `from app.models.scene import Scene` | +1 |
| `app/main.py` | Added `scenes_router` import + `app.include_router(scenes_router)` | +2 |

**No Sprint 1, 2, or 3 business logic was modified.**

---

## Database Changes

### New Table: `scenes`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, indexed |
| `episode_id` | Integer | FK → `episodes.id`, NOT NULL |
| `scene_number` | Integer | NOT NULL |
| `title` | String(255) | NOT NULL |
| `narration` | Text | nullable |
| `camera_notes` | Text | nullable |
| `duration_seconds` | Float | nullable |
| `status` | String(50) | NOT NULL, default `"draft"` |
| `created_at` | DateTime(tz) | NOT NULL, server_default `CURRENT_TIMESTAMP` |

### Migration Created

- **File:** `alembic/versions/164be27a3631_create_scenes_table.py`
- **Chain:** `80ba59d04bd7` (projects) → `d83f2f1f9a63` (stories) → `6a5cd883465f` (episodes) → `164be27a3631` (scenes)

---

## API Endpoints

| Method | Path | Success | Error | Notes |
|--------|------|---------|-------|-------|
| POST | `/episodes/{episode_id}/scenes` | 201 | 404 (episode missing), 422 (validation) | Creates scene under episode |
| GET | `/episodes/{episode_id}/scenes` | 200 | 404 (episode missing) | Returns scenes ordered by `scene_number ASC` |
| GET | `/scenes/{scene_id}` | 200 | 404 | Standalone lookup |

---

## Validation Rules

| Field | Rule | HTTP Status on Violation |
|-------|------|------------------------|
| `scene_number` | Must be > 0 (`gt=0`) | 422 |
| `title` | Required, non-empty (`min_length=1`) | 422 |
| `duration_seconds` | Optional, but if provided must be > 0 (`gt=0`) | 422 |
| `episode_id` (path) | Episode must exist | 404 |
| `scene_id` (path) | Scene must exist | 404 |

---

## Problems Faced

### None.

The architecture pattern established across Sprints 1–3 made this implementation entirely mechanical. Every file followed the same template. The only design consideration was making `duration_seconds` a `Float` (nullable, optional) with `gt=0` validation — since duration is a physical measurement that only makes sense when positive, but may not always be known at creation time.

---

## Lessons Learned

1. **The pattern scales cleanly to 4 levels deep.** Project → Story → Episode → Scene — each layer follows the identical model/schema/service/router structure. The hierarchy grows without added complexity.

2. **Optional fields with conditional validation work well.** `duration_seconds` is nullable but validated as `gt=0` when provided. Pydantic handles this cleanly — `None` passes, `0` and negatives get rejected with 422.

3. **Float vs Integer for duration.** We chose `Float` over `Integer` for `duration_seconds` because real-world scene durations include fractions (e.g., 15.5 seconds). This was the first Float column in the project.

4. **Cross-service import pattern is consistent.** Each router validates its parent resource exists by importing the parent's service: scenes → `get_episode_by_id`, episodes → `get_story_by_id`, stories → `get_project_by_id`. The pattern is predictable and easy to follow.

5. **Swagger automatically groups by tags.** FastAPI's tag system (`tags=["Scenes"]`) keeps the /docs UI organized as endpoint count grows. After 4 sprints (12 endpoints + health check), everything is clearly categorized.

---

## Test Results

Full regression test across all 4 sprints — **24 test cases, all passed:**

```
SPRINT 1: Projects
  POST /projects/         => 201 ✓
  GET  /projects/         => 200 ✓
  GET  /projects/{id}     => 200 ✓
  GET  /projects/99999    => 404 ✓

SPRINT 2: Stories
  POST /projects/{id}/stories  => 201 ✓
  GET  /projects/{id}/stories  => 200 ✓
  GET  /stories/{id}           => 200 ✓
  GET  /stories/99999          => 404 ✓

SPRINT 3: Episodes
  POST /stories/{id}/episodes  => 201 ✓
  GET  /stories/{id}/episodes  => 200 ✓
  GET  /episodes/{id}          => 200 ✓
  GET  /episodes/99999         => 404 ✓

SPRINT 4: Scenes
  POST /episodes/{id}/scenes (all fields)     => 201 ✓
  POST /episodes/{id}/scenes (minimal fields) => 201 ✓
  GET  /episodes/{id}/scenes                  => 200 ✓ (ordered by scene_number)
  GET  /scenes/{id}                           => 200 ✓
  GET  /scenes/99999                          => 404 ✓
  POST /episodes/99999/scenes                 => 404 ✓
  GET  /episodes/99999/scenes                 => 404 ✓
  POST scene_number=0                         => 422 ✓
  POST scene_number=-1                        => 422 ✓
  POST empty title                            => 422 ✓
  POST duration_seconds=0                     => 422 ✓
  POST duration_seconds=-5                    => 422 ✓
```

**Swagger UI:** Verified at `/docs` — all 4 tags (Projects, Stories, Episodes, Scenes) visible with all endpoints.

**Previous sprints confirmed working.** ✓

---

## Architecture Snapshot After Sprint 4

```
app/
├── api/
│   ├── projects.py      ← Sprint 1
│   ├── stories.py       ← Sprint 2
│   ├── episodes.py      ← Sprint 3
│   └── scenes.py        ← Sprint 4
├── models/
│   ├── __init__.py       ← registers all 4 models
│   ├── project.py        ← has stories relationship
│   ├── story.py          ← has project + episodes relationships
│   ├── episode.py        ← has story + scenes relationships
│   └── scene.py          ← has episode relationship + FK
├── schemas/
│   ├── project.py        ← Sprint 1
│   ├── story.py          ← Sprint 2
│   ├── episode.py        ← Sprint 3
│   └── scene.py          ← Sprint 4
├── services/
│   ├── project.py        ← Sprint 1 (reused by stories router)
│   ├── story.py          ← Sprint 2 (reused by episodes router)
│   ├── episode.py        ← Sprint 3 (reused by scenes router)
│   └── scene.py          ← Sprint 4
├── database/
│   ├── base.py           ← Base class
│   └── session.py        ← engine + get_db
├── core/
│   └── config.py         ← settings
└── main.py               ← registers all 4 routers

notes/
├── Sprint_02.md
├── Sprint_03.md
└── Sprint_04.md

alembic/versions/
├── 80ba59d04bd7_create_projects_table.py   ← Sprint 1
├── d83f2f1f9a63_create_stories_table.py    ← Sprint 2
├── 6a5cd883465f_create_episodes_table.py   ← Sprint 3
└── 164be27a3631_create_scenes_table.py     ← Sprint 4
```
