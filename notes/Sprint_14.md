# Sprint 14 — Generation Job System

**Date:** 2026-06-29  
**Branch:** `sprint-14-generation-job-system` (merged into `main`)  
**Commit Hash:** `2e64bd9` (`2e64bd9cb8f8cfba354032a9cafe9a651c675b51`)

---

## Files Created

| File | Change Type | Purpose |
|------|-------------|---------|
| `app/models/generation_job.py` | Created | SQLAlchemy model defining the `generation_jobs` table and its relationship to `Scene`. |
| `app/schemas/generation_job.py` | Created | Pydantic validation schemas (`GenerationJobCreate`, `GenerationJobResponse`, `GenerationJobProgress`, and `GenerationJobComplete`). |
| `app/services/generation_job.py` | Created | Service layer implementation managing job creation, retrieval, progress, and completion. |
| `app/api/jobs.py` | Created | API router exposing job lifecycle endpoints. |
| `alembic/versions/6fbecf8cb948_create_generation_jobs_table.py` | Created | Database migration script creating the `generation_jobs` table. |
| `notes/Sprint_14.md` | Created | Documentation journal for Sprint 14. |

---

## Database Schema

### New Table: `generation_jobs`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, indexed |
| `scene_id` | Integer | FK → `scenes.id`, NOT NULL |
| `shot_number` | Integer | NOT NULL |
| `provider` | String(100) | Nullable |
| `prompt` | Text | NOT NULL |
| `negative_prompt` | Text | Nullable |
| `filename` | String(255) | Nullable |
| `status` | String(50) | NOT NULL, default `"pending"` |
| `priority` | Integer | NOT NULL, default `0` |
| `retry_count` | Integer | NOT NULL, default `0` |
| `progress` | Integer | NOT NULL, default `0` |
| `drive_file_id` | String(255) | Nullable |
| `generation_time` | Float | Nullable |
| `created_at` | DateTime(tz) | NOT NULL, server_default `CURRENT_TIMESTAMP` |
| `updated_at` | DateTime(tz) | NOT NULL, server_default `CURRENT_TIMESTAMP`, onupdate `CURRENT_TIMESTAMP` |

---

## API Endpoints

| Method | Path | Status Code | Description |
|--------|------|-------------|-------------|
| POST | `/jobs` | 201 Created | Creates generation jobs for all shots in a scene using Prompt Engine output. |
| GET | `/jobs/next` | 200 OK | Fetches the oldest pending job and marks its status as `"processing"`. |
| PATCH | `/jobs/{id}/progress` | 200 OK | Updates the progress percentage of a job. |
| POST | `/jobs/{id}/complete` | 200 OK | Marks the job as `"completed"`, setting `drive_file_id` and `generation_time`. |

---

## Architecture & Lifecycle Flow

1. **Job Creation (`POST /jobs`):**
   Reads the storyboard and prompts from the Prompt Engine for a given `scene_id`. It creates one row in the `generation_jobs` table for each shot in the scene, initialized with the `"pending"` status.

2. **Job Acquisition (`GET /jobs/next`):**
   AI Studio Workers query this endpoint to grab work. It retrieves the oldest pending job (ordered by `priority DESC, created_at ASC`) and transitions its status to `"processing"` to ensure concurrency safety.

3. **Progress Updates (`PATCH /jobs/{id}/progress`):**
   Allows the worker to report progress back to the backend.

4. **Job Completion (`POST /jobs/{id}/complete`):**
   Once generation is done, the worker calls this to set the job status to `"completed"`, record the Google Drive file ID (`drive_file_id`), and store the duration taken (`generation_time`).

---

## Regression Verification

All endpoints from Sprints 1–14 have been verified via integration testing using a temporary database:
- **Projects:** Creation, retrieval, and configuration.
- **Stories & Episodes:** Relational mapping and retrieval.
- **Scene Management:** Creation and retrieval under episodes.
- **Character Registry:** Registration under stories.
- **Scene Character Mapping:** Assigning characters to scenes.
- **Story Blueprint:** Scene calculation and statistics.
- **Storyboard Generator:** Ordering shots and scene configurations.
- **Prompt Engine:** Generation of positive and negative prompts.
- **Image Provider Framework:** Generation of local mock images.
- **Asset Manager:** Subdirectory layout generation and file saving.
- **Generation Jobs:** Automatic creation, pending queue selection, progress update, and job completion.

**All 14 Sprint regression test cases passed successfully.**
