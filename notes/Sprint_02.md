# Sprint 02 — Story Management

**Date:** 2026-06-29
**Branch:** `sprint-1-project-management` (continued)

---

## What We Built

Added full Story Management on top of the existing Project Management foundation.

### Story Model (`app/models/story.py`)
- `id`, `project_id` (FK → `projects.id`), `title`, `genre`, `summary`, `story_text`, `status`, `version`, `created_at`
- `status` defaults to `"draft"`, `version` defaults to `1`
- Bidirectional relationship: `Story.project` ↔ `Project.stories`

### Schemas (`app/schemas/story.py`)
- `StoryCreate` — title required (`min_length=1`), genre/summary/story_text optional
- `StoryResponse` — full serialization with `from_attributes=True`

### Service Layer (`app/services/story.py`)
- `create_story(db, project_id, payload)` — insert + commit + refresh
- `get_stories_by_project(db, project_id)` — filtered + ordered newest first
- `get_story_by_id(db, story_id)` — returns `None` if missing

### API Endpoints (`app/api/stories.py`)
| Method | Path | Status | Notes |
|--------|------|--------|-------|
| POST | `/projects/{project_id}/stories` | 201 | Validates project exists first |
| GET | `/projects/{project_id}/stories` | 200 | Validates project exists first |
| GET | `/stories/{story_id}` | 200 / 404 | Standalone lookup |

### Migration
- `alembic/versions/d83f2f1f9a63_create_stories_table.py` — chains from Sprint 1's `80ba59d04bd7`

### Modified Files (Sprint 1 untouched)
- `app/models/project.py` — added `relationship` import + `stories` back_populates
- `app/models/__init__.py` — added `Story` import for Alembic detection
- `app/main.py` — added `stories_router` registration (2 lines only)

---

## Problems Faced

### 1. Alembic autogenerate producing empty migrations (Sprint 1 lesson carried forward)
In Sprint 1, the first migration was empty because `alembic/env.py` imported `Base` but no models were registered on `Base.metadata` yet. The fix was adding `import app.models` to `env.py`. This was already in place for Sprint 2, so the stories migration generated correctly on the first attempt.

### 2. Nested route design decision
The endpoints needed to be project-scoped (`/projects/{project_id}/stories`) for create and list, but standalone (`/stories/{story_id}`) for get-by-id. Rather than nesting the stories router under the projects router (which adds coupling), we used a flat router with explicit path strings. This keeps the router self-contained and avoids prefix conflicts.

### 3. Project existence validation
Both `POST` and `GET` on `/projects/{project_id}/stories` must validate that the project exists before proceeding. We reused `get_project_by_id` from the project service layer rather than duplicating the query — keeping services as the single source of truth for data access.

---

## What We Learned

1. **Architecture consistency pays off.** By mirroring Sprint 1's structure exactly (model → schema → service → router → register), Sprint 2 was implemented in one pass with zero structural decisions to make.

2. **Bidirectional relationships need both sides.** SQLAlchemy's `relationship()` with `back_populates` requires declarations on *both* models. Forgetting one side causes silent failures when navigating the relationship.

3. **Alembic migration chain integrity matters.** The `down_revision` in the stories migration correctly points to the projects migration (`80ba59d04bd7`). This ensures `alembic upgrade head` applies them in order and `alembic downgrade` can roll back cleanly.

4. **Validate parent resources in nested routes.** When creating a child resource under a parent (story under project), always verify the parent exists first and return 404 — don't let the database FK constraint throw a 500.

5. **Service reuse across routers is fine.** The stories router imports `get_project_by_id` from the project service. This is acceptable cross-service usage for read-only validation. If it grew more complex, a shared dependency or middleware would be cleaner.

---

## Architecture Snapshot After Sprint 2

```
app/
├── api/
│   ├── projects.py      ← Sprint 1
│   └── stories.py       ← Sprint 2
├── models/
│   ├── __init__.py       ← registers both models
│   ├── project.py        ← has stories relationship
│   └── story.py          ← has project relationship + FK
├── schemas/
│   ├── project.py        ← Sprint 1
│   └── story.py          ← Sprint 2
├── services/
│   ├── project.py        ← Sprint 1 (reused by stories router)
│   └── story.py          ← Sprint 2
├── database/
│   ├── base.py           ← Base class
│   └── session.py        ← engine + get_db
├── core/
│   └── config.py         ← settings
└── main.py               ← registers both routers
```
