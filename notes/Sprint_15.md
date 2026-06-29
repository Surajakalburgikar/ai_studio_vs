# Sprint 15 — Reporter System

**Date:** 2026-06-29  
**Branch:** `main` (backend) & `master` (worker)  

---

## Architecture Diagram

```mermaid
flowchart TD
    QueuePoller["Queue Poller (worker/queue/poller.py)"] -->|1. fetch_job()| JobFetcher["JobFetcher (worker/jobs/fetch.py)"]
    QueuePoller -->|2. process(job)| JobProcessor["JobProcessor (worker/jobs/process.py)"]
    JobProcessor -->|3. report_started(job)| Reporter["Reporter (worker/reporter/reporter.py)"]
    Reporter -->|4. update_job_progress(0%)| BackendClient["BackendClient (worker/backend/client.py)"]
    BackendClient -->|5. PATCH /jobs/{id}/progress| BackendAPI["Backend API"]
    JobProcessor -->|6. execute(job)| Executor["Executor (worker/execution/executor.py)"]
    Executor -->|7. generate(job)| MockProvider["Image Provider (worker/image_providers/mock.py)"]
    Executor -->|8. save_image(filename, image)| LocalStorage["Storage Provider (worker/storage/local.py)"]
    LocalStorage -->|9. returns path| Executor
    Executor -->|10. returns ExecutionResult| JobProcessor
    JobProcessor -->|11. report_progress(50%)| Reporter
    Reporter -->|12. update_job_progress(50%)| BackendClient
    JobProcessor -->|13. report_completed(job, result)| Reporter
    Reporter -->|14. complete_job()| BackendClient
    BackendClient -->|15. POST /jobs/{id}/complete| BackendAPI
    
    %% Error Flow
    JobProcessor -.->|On Exception: report_failed(job, error)| Reporter
    Reporter -.->|fail_job()| BackendClient
    BackendClient -.->|POST /jobs/{id}/failed| BackendAPI
```

---

## Files Created

### Backend (`AI_STUDIO`)
* `alembic/versions/f9025cd873c1_add_error_message_to_generation_jobs.py` — Database migration adding the `error_message` field.
* `verify_sprint_15.py` — End-to-end integration and regression verification script.
* `notes/Sprint_15.md` — Documentation for Sprint 15 reporter system implementation.

### Worker (`AI_STUDIO_WORKER`)
* `worker/reporter/__init__.py` — Exposes the `Reporter` class.
* `worker/reporter/reporter.py` — Core `Reporter` class managing job lifecycle notification.
* `worker/reporter/models.py` — Models and configurations for the reporter.

---

## Files Modified

### Backend (`AI_STUDIO`)
* `app/models/generation_job.py` — Added `error_message` column.
* `app/schemas/generation_job.py` — Added `GenerationJobFailed` schema and extended `GenerationJobResponse` to include `error_message`.
* `app/services/generation_job.py` — Implemented `mark_failed()` to mark a job status as `"failed"` and save the error message.
* `app/api/jobs.py` — Exposed `POST /jobs/{job_id}/failed` endpoint.

### Worker (`AI_STUDIO_WORKER`)
* `worker/backend/client.py` — Added HTTP methods for progress updates, completions, and failures using the existing requests client.
* `worker/execution/result.py` — Redefined `ExecutionResult` to have clean `success`, `provider`, `generation_time`, `image_path`, and `message` properties.
* `worker/execution/executor.py` — Modified to construct the simplified `ExecutionResult`.
* `worker/jobs/process.py` — Orchestrated the lifecycle pipeline calls using the new `Reporter`.

---

## Lessons Learned
1. **Unbuffered Stdout for Python in Background Processes:** In interactive environments or automation runners, python standard output is buffered when redirected/captured. Disabling buffering with the `-u` flag prevents delayed log updates.
2. **Priority-Driven Job Fetching:** When writing integration tests with a persistent test DB state, verify job priorities to ensure the queue poller fetches the expected job rather than older pending jobs with higher priorities.

---

## Regression Verification Status
All endpoints from Sprints 1–15 have been verified and passed successfully using `verify_sprint_15.py`:
- **Projects:** Creation, retrieval, and configuration validation.
- **Stories & Episodes:** Relational mappings and retrieval.
- **Scene Management:** Scene configurations and retrieval.
- **Character Registry:** Registration, mappings, and scene mapping.
- **Storyboard & Prompts:** Storyboard generation, positive/negative prompts.
- **Generation Jobs:** Automatic creation, status transitions, progress updates, completions.
- **New Feature Verification:** Direct endpoint calls to `POST /jobs/{job_id}/failed` successfully transition status to `"failed"` and write the `error_message`.
- **Pipeline End-to-End Verification:** Successful worker executions transition the job to `"completed"`, setting output path and generation time. Failed runs caught via exceptions transition the job status to `"failed"` on the backend and record the exact exception trace/message.
