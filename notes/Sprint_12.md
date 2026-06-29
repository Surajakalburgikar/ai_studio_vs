# Sprint 12 — Asset Manager

**Date:** 2026-06-29  
**Branch:** `sprint-12-asset-manager` (merged into `main`)  
**Commit Hash:** `884a260` (`884a260902701153713a00c047ff5f89fde320b6`)

---

## Files Created

| File | Change Type | Purpose |
|------|-------------|---------|
| `app/assets/manager.py` | Created | `AssetManager` class managing file layout creation, manifest creation, and file saving operations. |
| `app/assets/models.py` | Created | Schema representing the output structure (`AssetResponse`). |
| `app/assets/__init__.py` | Created | Package initialization exposing `AssetManager` and `AssetResponse`. |
| `app/api/assets.py` | Created | Router exposing `/scenes/{scene_id}/assets` endpoint. |
| `notes/Sprint_12.md` | Created | Documentation journal for Sprint 12. |

---

## Architecture & Layout Design

The `AssetManager` implements a structured workspace layout based on the relational database hierarchy:
- Base path: `generated/project_{project_id}/story_{story_id}/episode_{episode_id}/scene_{scene_id}/`
- Inside each scene workspace, the manager automatically spawns:
  - `prompts/`
  - `images/`
  - `voice/`
  - `subtitles/`
  - `clips/`
  - `manifest.json`

### Manifest Design
The manifest file automatically tracks generated filenames grouped by asset type:
```json
{
  "scene_id": 1,
  "prompts": [],
  "images": [],
  "voice": [],
  "subtitles": [],
  "clips": []
}
```

---

## Asset Manager Operations

The manager exposes file save operations that write the asset contents to their respective subdirectories and update the manifest:
1. `save_prompt(filename, content)`
2. `save_image(filename, content)`
3. `save_voice(filename, content)`
4. `save_subtitle(filename, content)`
5. `save_clip(filename, content)`

---

## Regression Status

All endpoints from Sprints 1-12 are fully verified and passing:
- **Projects:** Config creation and fetching.
- **Stories & Episodes:** Relational mappings.
- **Scenes:** Retrieval and configurations.
- **Blueprint:** Story blueprint calculations.
- **Characters:** Registry creation and scene-character assignments.
- **Storyboard Generator:** Ordered shot durations and transition details.
- **Prompt Engine:** Visual descriptive tags.
- **Image Provider Framework:** Mock image generation, local file storage, and active provider delegation.
- **Asset Manager:** Nesting layouts creation, asset listing, manifest generation, and asset-saving endpoints.
