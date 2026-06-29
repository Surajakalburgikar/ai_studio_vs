# Sprint 03 — Episode Management

**Date:** 2026-06-29  
**Branch:** `sprint-1-project-management` (continued)

---

## What We Built

Added Episode Management, the third layer in the hierarchy: **Project → Story → Episode**.

### Episode Model (`app/models/episode.py`)
- `id`, `story_id` (FK → `stories.id`), `episode_number`, `title`, `summary`, `status`, `created_at`
- `status` defaults to `"draft"`
- Bidirectional relationship: `Episode.story` ↔ `Story.episodes`

### Schemas (`app/schemas/episode.py`)
- `EpisodeCreate` — `episode_number` required (`gt=0`), `title` required (`min_length=1`), `summary` optional
- `EpisodeResponse` — full serialization with `from_attributes=True`

### Service Layer (`app/services/episode.py`)
- `create_episode(db, story_id, payload)` — insert + commit + refresh
- `get_story_episodes(db, story_id)` — filtered, ordered by `episode_number` ascending
- `get_episode_by_id(db, episode_id)` — returns `None` if missing

### API Endpoints (`app/api/episodes.py`)
| Method | Path | Status | Notes |
|--------|------|--------|-------|
| POST | `/stories/{story_id}/episodes` | 201 | Validates story exists first |
| GET | `/stories/{story_id}/episodes` | 200 | Validates story exists first |
| GET | `/episodes/{episode_id}` | 200 / 404 | Standalone lookup |

### Migration
- `alembic/versions/6a5cd883465f_create_episodes_table.py` — chains from Sprint 2's `d83f2f1f9a63`

### Modified Files (Sprint 1 & 2 logic untouched)
- `app/models/story.py` — added `episodes = relationship("Episode", back_populates="story")` (1 line)
- `app/models/__init__.py` — added `Episode` import (1 line)
- `app/main.py` — added `episodes_router` import + `include_router` (2 lines)

---

## Problems Faced

### 1. No problems this sprint
The architecture pattern established in Sprint 1 and reinforced in Sprint 2 made Sprint 3 completely mechanical. Every file followed the same template: model → schema → service → router → register → migrate. Zero surprises.

### 2. Ordering decision: episode_number vs created_at
For episodes, we chose `ORDER BY episode_number ASC` instead of `created_at DESC` (used in projects and stories). This is because episodes have an explicit sequence — users care about narrative order, not insertion order. This is the first time the service layer deviated from the previous pattern, and it was the right call.

---

## What We Learned

1. **Consistent architecture eliminates decision fatigue.** By Sprint 3, the implementation was pure execution — no design decisions, no file structure debates. The pattern is now muscle memory.

2. **Pydantic's `Field(gt=0)` is cleaner than manual validation.** Instead of checking `episode_number > 0` in the service layer or router, we declared it in the schema. FastAPI auto-returns 422 with a clear error message. Validation belongs at the boundary.

3. **The migration chain is growing predictably.** Three migrations now: `80ba59d04bd7` (projects) → `d83f2f1f9a63` (stories) → `6a5cd883465f` (episodes). Each `down_revision` correctly points to its predecessor. `alembic upgrade head` applies them in sequence.

4. **Cross-service imports remain read-only.** The episodes router imports `get_story_by_id` from the story service (just as the stories router imports `get_project_by_id` from the project service). This pattern is consistent and keeps validation logic centralized.

5. **Ordering strategy should match domain semantics.** Projects/stories use `created_at DESC` (newest first). Episodes use `episode_number ASC` (narrative order). The service layer is the right place to encode this domain knowledge.

---

## Migration Chain

```
80ba59d04bd7  (Sprint 1: projects)
      ↓
d83f2f1f9a63  (Sprint 2: stories)
      ↓
6a5cd883465f  (Sprint 3: episodes)
```

## Architecture Snapshot After Sprint 3

```
app/
├── api/
│   ├── projects.py      ← Sprint 1
│   ├── stories.py       ← Sprint 2
│   └── episodes.py      ← Sprint 3
├── models/
│   ├── __init__.py       ← registers all 3 models
│   ├── project.py        ← has stories relationship
│   ├── story.py          ← has project + episodes relationships
│   └── episode.py        ← has story relationship + FK
├── schemas/
│   ├── project.py        ← Sprint 1
│   ├── story.py          ← Sprint 2
│   └── episode.py        ← Sprint 3
├── services/
│   ├── project.py        ← Sprint 1 (reused by stories router)
│   ├── story.py          ← Sprint 2 (reused by episodes router)
│   └── episode.py        ← Sprint 3
├── database/
│   ├── base.py           ← Base class
│   └── session.py        ← engine + get_db
├── core/
│   └── config.py         ← settings
└── main.py               ← registers all 3 routers
```
