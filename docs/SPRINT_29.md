# Sprint 29 — Production Orchestrator & Continuity Layer

## Objective
Implement a production orchestration and continuity layer that makes the AI Studio pipeline safe for long-running, multi-part story productions. Specifically, this sprint covers:
1. Long-term story continuity manifest (characters, locations, facts, preferred models, and checkpoints).
2. Production orchestration state tracking (run/checkpoint lifecycle: start, pause, resume, finish).
3. Quality-preserving provider policy (modes: production, testing, development) to prevent silent downgrades of image quality.
4. Continuity-aware job resume/pauses.
5. Continuity mapping for sequels (Part 2 / Part 3).
6. Backend FastAPI api endpoints for production state control.
7. Worker policy updates to respect exact transport/model specs, perform same-model transport fallbacks, and report actual generation details.

---

## Architecture Design

### 1. Continuity Manifest (`app/services/ai/continuity/`)
- `ContinuityManifest`: Dataclass containing the canonical universe states, character visual properties, facts, timeline anchors, and run positions.
- `ContinuityManager`: Manages file-based loading, saving, cloning, importing, and exporting of the manifests (defaulting to the `./continuity` path).
- `ContinuityResolver`: Resolves scene context character name queries and updates visual property fields before rendering prompts.

### 2. State Orchestrator (`app/services/ai/orchestrator/`)
- `ProductionCheckpoint` & `ProductionRun`: Tracks the running states, current job ID, scene, and last completed step.
- `ProductionStateManager`: Saves and retrieves run and checkpoint states in the background.
- `ProductionOrchestrator`: Main life-cycle coordinator orchestrating runs (`start_production`, `pause_production`, `resume_production`, `continue_as_new_project`, `finish_production`).

### 3. Provider Policies (`app/services/ai/policies/`)
- `ProviderPolicy`: Evaluates matching model and transport configurations against availability.
  - **Production Mode**: Fails closed if the exact model is not available. Same-model transport fallback (e.g. `fal-ai` -> `huggingface`) is permitted.
  - **Development Mode**: Permits quality downgrades (e.g. `FLUX.1-dev` -> `FLUX.1-schnell`) if explicitly enabled.

---

## API Endpoints
The following endpoints are registered under `/production`:
- `POST /production/start?project_id=X`: Start a production run.
- `POST /production/{continuity_key}/pause?reason=Y`: Pause production.
- `POST /production/{continuity_key}/resume`: Resume production.
- `POST /production/continue-project?from_project_id=A&new_project_id=B`: Continue story universe as a new project (sequel).
- `GET /production/{continuity_key}/manifest`: Query continuity manifest.
- `GET /production/{continuity_key}/checkpoint`: Query latest checkpoint.
- `GET /production/{continuity_key}/status`: Query current run status.

---

## Verification Results
Verification tests were executed successfully using `verify_sprint_29.py`:
```
Ran 5 tests in 12.627s

OK
```
Tests covered:
- Continuity manifest serialization & file operations.
- State orchestrator lifecycle (start, pause, resume, continue_as_new_project).
- Provider policy route evaluations under production & development modes.
- Character registry integration resolving visual properties via ContinuityResolver.
- Worker execution respecting job specs and reporting exact transport/model details.
