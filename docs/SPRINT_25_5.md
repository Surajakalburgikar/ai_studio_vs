# Sprint 25.5 — Pipeline Contract & Prompt Foundation

This document details the architecture design, contract changes, and modular prompting strategies introduced in Sprint 25.5.

---

## 1. Architecture Review

The primary focus of Sprint 25.5 is establishing a stable, future-proof API contract between the backend story generation pipeline and the rendering worker agents. 

Previously, stages passed around loose, unvalidated metadata dictionaries containing prompt strings and image configurations. This sprint formally introduces two primary domain objects:
1. `PromptBundle`: Represents a modular, category-based collection of positive and negative prompt fragments (style, camera, character traits, composition, lighting, environment, quality).
2. `GenerationSpecification`: Represents the single, versioned payload containing all generation instructions, models, providers, prompt bundles, and storage configurations required by a worker.

---

## 2. Problems Solved

* **Hardcoded Prompt Strings**: Before, prompts were simple, concatenated strings created early in the pipeline. This made it difficult for downstream stages (like character consistency engines or shot planners) to modify specific descriptors without brittle regex string replacements.
* **Worker Payload Redundancy**: In previous plans, there was a distinction between backend generation specifications and worker payloads. By unifying them into `GenerationSpecification`, the worker and backend exchange the exact same structure, reducing serialization and parsing overhead.
* **Lack of Versioning**: The contract now includes an explicit `version` field (defaulting to `"1.0"`). Future workers can inspect this field to invoke legacy or advanced parsing pipelines depending on structural upgrades.
* **Visual Trait Fabrication**: The character profile builder now strictly avoids inventing traits (like hair style or eye color) unless explicitly defined in the source script/narrative. Additionally, a new `current_visual_state` tracking container maintains active shot-level attributes (outfit, pose, expressions).

---

## 3. Old vs New Flow

### Old Flow
```text
Project -> Story -> SceneDirection (loose metadata) -> ShotPlan (loose metadata) -> WorkerPayload (concatenated prompt string)
```

### New Flow
```text
Project -> Story -> SceneDirection -> ShotPlan -> CharacterProfile (with visual continuity states) -> PromptBundle (modular) -> GenerationSpecification (versioned contract) -> Worker
```

---

## 4. Prompt Composition Strategy (Future PromptBuilder)

When implemented, the `PromptBuilder` will compile modular `PromptBundle`s by evaluating multiple inputs:

1. **Base Quality and Style**: Inherited from the `Project` global presets (e.g., `art_style="anime"` + quality tags like `"masterpiece", "detailed scenery"`).
2. **Kinetic Context**: Inherited from the `ShotPlan` framing and camera tags (e.g., `shot_type="Close-up"` + `camera_movement="Static"`).
3. **Visual Continuity**: Inherited from `CharacterProfile` traits and the current `current_visual_state` (e.g., matching the protagonist's outfit, expression, and active props).
4. **Scene Setting**: Inherited from `SceneDirection` environment and lighting guidelines.

These segments are dynamically mapped to categories in the `PromptBundle` and only concatenated into a comma-separated prompt string at export time inside the worker.

---

## 5. Worker Contract

* The `GenerationSpecification` is the **only** payload exchanged between the backend queue and worker agents.
* All worker-specific metadata (lease times, retry counters, task execution timestamps) must be stored inside the `metadata` dictionary to keep the core parameters pristine and immutable.
