# Sprint 31.2: Gemini Runtime, Persistence, and Model Pinning

This document covers the details of the persistent model router, runtime statistics, project preferred model pinning, and system routing APIs implemented in Sprint 31.2.

---

## 1. Persistent Router State & Statistics

The model router dynamically updates its health status and records runtime metrics to state files in `app/runtime/`.

### State File (`app/runtime/gemini_router_state.json`)
Saves cooldown bounds, last success model, last failure reason, and failure timestamps:
```json
{
  "_metadata": {
    "last_successful_model": "gemini-2.5-flash",
    "last_failure_reason": "quota_exhausted"
  },
  "gemini-2.5-flash": {
    "cooldown_until": "2026-07-01T15:32:36+00:00",
    "last_failure": "quota_exhausted",
    "failure_timestamp": "2026-07-01T14:32:36+00:00"
  }
}
```

### Statistics File (`app/runtime/gemini_router_stats.json`)
Tracks metrics per-model:
```json
{
  "gemini-2.5-flash": {
    "requests": 10,
    "successful requests": 8,
    "failed requests": 2,
    "429 count": 1,
    "quota exhausted count": 1,
    "timeout count": 0,
    "average latency": 150.2,
    "last used timestamp": "2026-07-01T14:32:36+00:00",
    "last successful timestamp": "2026-07-01T14:31:36+00:00",
    "cooldown activations": 1
  }
}
```

---

## 2. Project Model Pinning

Projects support an optional `preferred_story_model` column.

### Behavior:
1. **Initial State (Unpinned)**:
   - When generating a story, the router's priority list determines the model.
   - Upon successful completion, the model (e.g. `gemini-2.5-flash`) is **automatically pinned** to the project's `preferred_story_model`.
2. **Subsequent Runs**:
   - The provider attempts the pinned model first.
   - If the pinned model fails or is on cooldown, it automatically falls back to the router's priority selection.
   - Pinned models are never overwritten automatically unless explicitly requested.

---

## 3. Router System APIs

The following management endpoints are exposed under `/system/gemini`:

### `GET /system/gemini/router`
Returns current active model, cooldown models, priority ordering, and per-model statistics.

### `GET /system/gemini/stats`
Returns aggregated summaries (failures, latency, rate limits, cooldowns, success rates) overall and per model.

### `GET /system/gemini/health`
Returns lists of healthy models, cooling down models, and the general router status (`healthy`, `degraded`, or `unavailable`).
