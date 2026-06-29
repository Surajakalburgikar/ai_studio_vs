# Sprint 09 — Storyboard Generator

**Date:** 2026-06-29  
**Branch:** `sprint-9-storyboard-generator` (merged into `main`)  
**Commit Hash:** `ab2f0ca` (`ab2f0ca6ab9da8368506e5f874e257870b044951`)

---

## Files Changed

| File | Change Type | Purpose |
|------|-------------|---------|
| `app/schemas/storyboard.py` | Created | Storyboard Pydantic validation schemas (`StoryboardShot`, `StoryboardResponse`). |
| `app/storyboard/storyboard_generator.py` | Created | Dynamic storyboard generation logic with deterministic shot generation rules. |
| `app/api/storyboard.py` | Created | Storyboard API router with GET endpoint. |
| `app/main.py` | Modified | Imported and registered `storyboard_router`. |
| `notes/Sprint_09.md` | Created | Documentation journal for Sprint 9. |

---

## Storyboard Format

A storyboard is generated dynamically from a Scene without storing any additional rows in the database.

### Shot Definition

Each shot contains:
- `shot_number` (integer: sequential index starting from 1)
- `shot_type` (string: "Wide" for establishing shot, "Close-up" for final shot, "Medium" for intermediate shots)
- `camera_angle` (string: "High Angle" for establishing shot, "Low Angle" for final shot, "Eye Level" for intermediate shots)
- `duration_seconds` (float: scene duration divided evenly by total shots)
- `focus_characters` (list of strings: names of the characters in focus)
- `description` (string: descriptive text detailing art style, aspect ratio, camera shot type, focus characters, narration, and voice configuration)
- `transition` (string: "Fade Out" for final shot, "Cut" for intermediate shots)

### Deterministic Generation Rules

1. **Shot Count:** If characters are present, `num_shots = max(3, len(characters) + 1)`. If no characters, `num_shots = 3`.
2. **Shot Durations:** Distribute `scene.duration_seconds` (defaulting to `10.0` if `None` or `<= 0`) evenly across the shots.
3. **Focus Characters Distribution:**
   - Shot 1: All characters in the scene.
   - Intermediate Shots: Individual character at index `(i - 2) % len(characters)`.
   - Final Shot: The first character.
4. **Description Formatting:** Constructed dynamically using project level properties (e.g. `art_style`, `aspect_ratio`, `language`, `voice_gender`), scene level attributes (`title`, `narration`), and the character names.

---

## Example Response (`GET /scenes/1/storyboard`)

```json
{
  "scene_id": 1,
  "scene_title": "Intro Scene",
  "project_id": 1,
  "project_title": "Project Alpha",
  "shots": [
    {
      "shot_number": 1,
      "shot_type": "Wide",
      "camera_angle": "High Angle",
      "duration_seconds": 5.17,
      "focus_characters": ["Z-100"],
      "description": "In manhwa style, framed in 9:16 aspect ratio. An establishing wide shot of the scene 'Intro Scene'. Narration: 'In the beginning...'. Audio voicing configured in Spanish (female).",
      "transition": "Cut"
    },
    {
      "shot_number": 2,
      "shot_type": "Medium",
      "camera_angle": "Eye Level",
      "duration_seconds": 5.17,
      "focus_characters": ["Z-100"],
      "description": "In manhwa style, framed in 9:16 aspect ratio. A medium shot focusing on Z-100. Narration: 'In the beginning...'. Audio voicing configured in Spanish (female).",
      "transition": "Cut"
    },
    {
      "shot_number": 3,
      "shot_type": "Close-up",
      "camera_angle": "Low Angle",
      "duration_seconds": 5.17,
      "focus_characters": ["Z-100"],
      "description": "In manhwa style, framed in 9:16 aspect ratio. A detailed close-up shot focusing on Z-100. Narration: 'In the beginning...'. Audio voicing configured in Spanish (female).",
      "transition": "Fade Out"
    }
  ]
}
```

---

## Lessons Learned

1. **SQLAlchemy Enum formatting:** SQLEnum fields might return the enum member instance instead of the raw string when retrieved from Python. Implementing a safe value-extraction utility (`hasattr(val, "value")`) ensures the raw string is correctly formatted under all Python runtimes.
2. **Guarding against Zero Division:** When dynamically dividing elements by list lengths (e.g. `len(characters)`), checking if list is empty prevents runtime `ZeroDivisionError` issues when a scene has no characters assigned.

---

## Regression Status

All endpoints from Sprints 1-9 are fully verified and passing:
- **Projects:** Management operations and config validation work.
- **Stories & Episodes:** Story/Episode hierarchy holds.
- **Scenes:** Operations function correctly.
- **Blueprint:** compilation and stats work with no regressions.
- **Characters:** Registry creation and mapping to scenes works.
- **Storyboard Generator:** Retrieve dynamic storyboards with correct structure and 404 validation.
