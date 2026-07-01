# Continuity Management Guide

This document describes how to configure, control, and monitor long-lived stories and universes in AI Studio.

---

## 1. The Story Continuity Manifest
A story universe is uniquely identified by a `continuity_key` (e.g. `con_a39b2cf48d1e`). Each universe is defined by a `ContinuityManifest` JSON file stored in the export folder (default: `./continuity`):

```json
{
  "continuity_key": "con_a39b2cf48d1e",
  "series_title": "The Ruins of Eldoria",
  "universe_title": "Universe of Eldoria",
  "continuity_version": 1,
  "canonical_characters": {
    "elara": {
      "name": "Elara",
      "description": "Elara the archer",
      "hair_style": "braided ponytail",
      "hair_color": "silver-white",
      "eye_color": "emerald green",
      "clothing": "leather armor"
    }
  },
  "canonical_locations": {},
  "canonical_facts": [
    "The Magic Core is located underneath the ancient temple."
  ],
  "timeline_anchor": {},
  "last_project_id": 1,
  "last_episode_number": 1,
  "last_scene_number": 3,
  "last_shot_number": 2
}
```

---

## 2. Production Lifecycles

### Starting a Production Run
When a new project is created, calling the `/production/start` endpoint kicks off the run.
- Generates a new `continuity_key` if the project does not have one.
- Creates a new `ContinuityManifest` file.
- Saves the initial active `ProductionRun` and `ProductionCheckpoint`.

### Pausing and Resuming
For long-running story generations:
- **Pause**: Calling `/production/{key}/pause` transitions all pending/processing generation jobs to `"paused"` state.
- **Resume**: Calling `/production/{key}/resume` transitions paused jobs back to `"pending"`, allowing worker poller agents to pick them up from the first incomplete shot.

### Continuing Sequels (Part 2 / Part 3)
To continue a story universe months later in a new project:
- Call `/production/continue-project?from_project_id=A&new_project_id=B`.
- Links the new project `B` to a cloned copy of the manifest with an incremented version (e.g. `con_key_v2`).
- Reuses all canonical characters, locations, facts, and timeline anchors from Part 1, guaranteeing absolute consistency.

---

## 3. Quality Preservation Policies
To prevent silent downgrades of render quality, the orchestrator evaluates every generation specification against configured mode settings:

| Pipeline Mode | Allow Downgrade | Behavior on Unavailability |
| :--- | :--- | :--- |
| `production` | `False` | **Fail Closed**: Rejects the job entirely if the exact model cannot be served. |
| `development` | `True` | **Downgrade Allowed**: Falls back to lower-resolution/lower-quality models (e.g. `schnell`). |
| `testing` | `False` / `True` | Custom fallback paths according to project settings. |

### Fallback Routing Hierarchy
1. **Exact Match**: Requested Model + Requested Transport (e.g. `FLUX.1-dev` via `fal-ai`).
2. **Transport Fallback**: Requested Model via first available alternative transport (e.g. `FLUX.1-dev` via `huggingface` serverless). Allowed in all modes.
3. **Model Downgrade**: Fallback to lower-quality model (e.g. `FLUX.1-schnell` via `huggingface`). Allowed only in dev/test modes when explicitly permitted.
