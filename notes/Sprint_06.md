# Sprint 06 — Story Blueprint

**Date:** 2026-06-29  
**Branch:** `sprint-6-story-blueprint` (merged into `main`)  
**Commit Hash:** `557dd56` (`557dd56d614a90d37975ae62168f6449e5e90241`)

---

## Files Created

| File | Purpose |
|------|---------|
| `app/blueprint/story_blueprint.py` | New module containing schema, routing, and calculations to compile a story's blueprint. |
| `notes/Sprint_06.md` | Development journal for Sprint 6. |

## Files Modified

| File | Change Description |
|------|--------------------|
| `app/main.py` | Imported `blueprint_router` and registered the new route `app.include_router(blueprint_router)`. |

*Note: Previous business logic, models, database schemas, and migration files were completely untouched.*

---

## API Endpoint

### `GET /stories/{story_id}/blueprint`

- **Purpose:** Compiles a structured, analytical summary of a story, its episodes, and their associated scenes to serve as a source of truth for downstream generations.
- **HTTP Success Code:** `200 OK`
- **HTTP Error Code:** `404 Not Found` (if the `story_id` is invalid)

---

## Blueprint Format

The endpoint returns JSON representation of `BlueprintResponse` schema:

```json
{
  "story_id": 1,
  "story_title": "Epic Legend of Testing",
  "total_episodes": 2,
  "total_scenes": 3,
  "total_estimated_duration_seconds": 60.0,
  "total_estimated_duration_minutes": 1.0,
  "average_scene_duration": 20.0,
  "ordered_episode_numbers": [1, 2],
  "ordered_scene_numbers_by_episode": {
    "1": [1, 2],
    "2": [1]
  }
}
```

---

## Lessons Learned

1. **Calculations in Memory vs Database Queries:** Instead of constructing complex joins or database aggregations directly, we loaded the model relationships (using ORM capabilities) and computed statistics (total scenes, average duration, order indices) in the service/routing layer. This approach is highly flexible, easy to debug, and performs well for moderately sized hierarchies.
2. **Handling Nullable Values in Calculations:** Since `duration_seconds` is optional and defaults to `None`, we explicitly verified and skipped/handled `None` values (treating them as `0.0` or filtering) to avoid raising python `TypeError` exceptions during math operations.
3. **JSON Dict Key Serialization:** Even though the Pydantic type is `dict[int, list[int]]`, standard JSON serializers automatically convert numeric keys (e.g. `1`, `2`) to string representations (e.g. `"1"`, `"2"`). Testing should check for stringified keys when inspecting JSON payload structures.

---

## Regression Status

All previous sprint endpoints are intact and fully functional:
- **Projects:** Creating/listing projects works successfully.
- **Stories:** Creating stories under projects works successfully.
- **Episodes:** Creating episodes under stories works successfully.
- **Scenes:** Creating scenes under episodes works successfully.
- **Blueprint:** Verified under empty and populated stories; validation rules successfully trigger 404 responses.
