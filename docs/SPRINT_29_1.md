# Sprint 29.1 — Architecture Refinement & Long-Term Continuity

## Objective
A pure refinement sprint that eliminates future technical debt before the Asset Registry (Sprint 30). It establishes robust continuity manifests, versioned character states, narrative timelines, and render profiles. All changes maintain 100% backward compatibility.

---

## 1. Updated File Tree

```
app/services/ai/
├── continuity/
│   ├── __init__.py                  ← exports all new types
│   ├── continuity_manifest.py       (unchanged)
│   ├── continuity_snapshot.py       (unchanged)
│   ├── continuity_manager.py        ← UPDATED: revision history, timeline/profile persistence, state versioning APIs
│   ├── continuity_resolver.py       ← UPDATED: canonical/state split, state helpers
│   ├── canonical_character.py       ← UPDATED: versioned CharacterState, CharacterProfile history, immutable ID
│   ├── manifest_revision.py         ← NEW: RevisionHistory dataclass
│   ├── revision_manager.py          ← NEW: append / list / restore revision history
│   └── narrative_timeline.py        ← UPDATED: NarrativeTimeline with revision & state version linkage
└── policies/
    ├── __init__.py                  ← exports QualityProfile, RenderProfile types
    ├── quality_mode.py              (unchanged)
    ├── provider_route.py            (unchanged)
    ├── provider_policy.py           ← UPDATED: RenderProfile -> QualityProfile -> ProviderPolicy hierarchy
    ├── quality_profile.py           ← NEW: QualityProfile enum + configs
    └── render_profile.py            ← NEW: RenderPreset model, scheduler, template & preset registry
```

---

## 2. RenderProfile Architecture (Task 3 & 4)

`RenderProfile` represents a complete rendering preset that decouples project configuration from concrete model names. Projects reference a `RenderProfile` by name (e.g. `anime_production`), which in turn references the actual model name (e.g. `black-forest-labs/FLUX.1-dev`). This ensures future model upgrades (like migrating to new versions of FLUX or other models) can be done by changing only the profile definition, without touching any project records.

### Built-in Anime Presets

| RenderProfile | Quality Tier | Preferred Model | Preferred Transport | Width/Height | Steps | Guidance | Style Template |
|---|---|---|---|---|---|---|---|
| **`anime_draft`** | `quick_draft` | `FLUX.1-schnell` | `huggingface` | 512x288 | 15 | 3.5 | `anime style, cel-shading, flat colors` |
| **`anime_preview`** | `preview` | `FLUX.1-schnell` | `huggingface` | 768x432 | 28 | 5.0 | `anime style, vibrant colors, detailed line art` |
| **`anime_production`** | `production` | `FLUX.1-dev` | `fal-ai` | 1024x576 | 50 | 7.5 | `anime style, cinematic lighting, highly detailed, 4k` |
| **`anime_master`** | `master` | `FLUX.1-dev` | `fal-ai` | 2048x1152 | 60 | 8.5 | `anime style, ultra-detailed, cinematic, masterpiece` |

---

## 3. Character State Version Lifecycle (Task 1)

`CharacterProfile` now cleanly separates the immutable `CanonicalCharacter` identity from a history of versioned `CharacterState` records. Every state update bumps the version and appends a new state to the list, ensuring previous states are never overwritten and remain accessible for flashbacks.

```mermaid
stateDiagram-v2
    [*] --> Version1 : create_character_state("apprentice robes")
    Version1 --> Version2 : update_character_state("knight armor", reason="Knighted")
    Version2 --> Version3 : update_character_state("king robes", reason="Crowned")
    Version3 --> Version4 : restore_character_state_version(1, reason="Flashback")
    note right of Version4
        Copies "apprentice robes" into Version 4.
        Original Version 1 is preserved untouched.
    end note
```

---

## 4. Timeline Revision Linkage (Task 2)

`TimelineEvent` is extended to log the active **continuity manifest revision** and the **character state versions** at the moment the event occurs. This provides complete context when generating flashbacks or performing continuity rollbacks.

```mermaid
graph TD
    subgraph Manifest Revisions
        R1[Revision 1: Initial World]
        R2[Revision2: Sequel setup]
    end

    subgraph Character State History
        C1[Elara V1: Apprentice]
        C2[Elara V2: Knight]
    end

    subgraph Timeline Event Linkage
        E1[Event: Scene 1 Battle]
        E1 -->|continuity_revision| R1
        E1 -->|character_state_versions| C1
        
        E2[Event: Scene 2 Sequel]
        E2 -->|continuity_revision| R2
        E2 -->|character_state_versions| C2
    end
```

---

## 5. System Diagrams

### Class Diagram

```mermaid
classDiagram
    class CanonicalCharacter {
        +str character_id
        +str canonical_name
        +str hair_color
        +str eye_color
        +dict metadata
    }
    class CharacterState {
        +int state_version
        +str current_outfit
        +str current_expression
        +str updated_at
        +str state_reason
        +bump_version(reason) CharacterState
    }
    class CharacterProfile {
        +CanonicalCharacter identity
        +CharacterState current_state
        +list state_history
        +update_state(reason, **kwargs)
        +restore_state_version(version) bool
    }
    class TimelineEvent {
        +str event_id
        +str description
        +int continuity_revision
        +dict character_state_versions
    }
    class RenderProfile {
        +str name
        +str quality_profile
        +str preferred_model
        +str preferred_transport
        +int steps
        +float guidance_scale
        +str style_template
        +resolve_quality_config() QualityProfileConfig
    }
    class ProviderPolicy {
        +str mode
        +RenderProfile render_profile
        +select_route(model, transport, available) Tuple
    }
    
    CharacterProfile *-- CanonicalCharacter
    CharacterProfile *-- CharacterState : current
    CharacterProfile *-- CharacterState : history
    ProviderPolicy *-- RenderProfile
```

### Render Profile Policy Hierarchy

```mermaid
graph TD
    A[RenderProfile Preset name: anime_production]
    A -->|1. resolve model/transport/params| B[FLUX.1-dev on fal-ai]
    A -->|2. resolve quality tier| C[QualityProfile: production]
    C -->|3. enforce fallback & quality rules| D[ProviderPolicy]
    D -->|4. execute / pause / fail| E[GenerationJob Spec Payload]
```

---

## 6. Migration Strategy (Task 5)

1. **Automatic Conversion**: If an existing project has no associated `RenderProfile`, the system calls `RenderProfile.from_quality_profile(quality_profile)` to automatically create a compatible rendering preset.
2. **Backward Compatibility**: `ProviderPolicy` constructors degrade gracefully when no `render_profile` is provided, pulling settings from the legacy `quality_profile` or individual parameters.
3. **Flat Dictionaries**: `CharacterProfile.from_dict()` maps legacy flat keys (like `clothing`) to `state.current_outfit` automatically.
4. **Key Preservation**: Sequels share the same `continuity_key` and register entries via the revision history list rather than duplicating files. `clone_manifest` remains as a deprecated interface emitting `DeprecationWarning`.
