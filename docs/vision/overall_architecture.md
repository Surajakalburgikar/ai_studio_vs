# Overall Architecture

AI Studio is structured as a decoupled, modular system consisting of a main API backend and one or more independent worker instances. This decoupling ensures that heavy AI inference tasks do not block web request handling or database transactions.

## Component Overview

```mermaid
flowchart TD
    Client["Client / UI"] <-->|"REST API"| Backend["FastAPI Backend (AI_STUDIO)"]
    Backend <-->|"SQLAlchemy (SQLite / PostgreSQL)"| Database[("Database")]
    Worker["Worker Service (AI_STUDIO_WORKER)"] -->|"REST Poll: /jobs/next"| Backend
    Worker -->|"REST Update: /jobs/{id}/progress"| Backend
    Worker -->|"REST Complete: /jobs/{id}/complete"| Backend
    Worker -->|"Hugging Face Inference API"| HF["Hugging Face (FLUX)"]
    Worker -->|"Storage Provider (Local / Cloud)"| Storage[("Image Storage")]
```

### 1. Main Backend (`AI_STUDIO`)
The backend is a FastAPI application managing the core data models, business logic, prompt building engine, and job queue.
* **REST API:** Serves endpoints for projects, stories, episodes, scenes, characters, and storyboard generation.
* **Database (SQLAlchemy):** Persists the structural hierarchy (Project → Story → Episode → Scene). Includes a unified `timeline_events` table for scene directing events.
* **Prompt Builder Engine:** Dynamically constructs detailed positive and negative prompts based on scene descriptions, camera parameters, and character visual attributes.
* **Job Queue:** Provides a simple priority queue where jobs are created for each storyboard shot and stored in the database as `pending`.

### 2. Worker Service (`AI_STUDIO_WORKER`)
The worker is a lightweight Python service designed to poll the backend, perform heavy tasks, and upload/save results.
* **Queue Poller:** Periodically queries `/jobs/next` on the backend.
* **Executor:** Coordinates image generation and storage.
* **Image Providers:** Abstracted modules implementing `BaseImageProvider`. Currently supports `MockProvider` and `FluxProvider` (Hugging Face Inference).
* **Storage Providers:** Abstracted modules implementing `BaseStorage`. Currently supports `LocalStorage` (saving to disk).
* **Reporter:** Handles calling progress and completion API endpoints on the backend to keep the job lifecycle updated.

## Job Lifecycle

```mermaid
sequenceDiagram
    participant B as Backend
    participant W as Worker
    participant P as Provider (Flux)
    participant S as Storage (Local)

    B->>B: Create Generation Jobs (status=pending)
    loop Polling
        W->>B: GET /jobs/next
        alt Job Available
            B-->>W: Return GenerationJob (status=processing)
        else No Job
            B-->>W: 404 Not Found (sleep & retry)
        end
    end
    W->>B: PATCH /jobs/{id}/progress (progress=0)
    W->>P: generate(job)
    Note over P: HF Inference API Call
    P-->>W: Return PIL.Image
    W->>B: PATCH /jobs/{id}/progress (progress=50)
    W->>S: save_image(filename, image)
    S-->>W: Return absolute/relative path
    W->>B: POST /jobs/{id}/complete (drive_file_id, generation_time)
    Note over B: Status set to completed
```
