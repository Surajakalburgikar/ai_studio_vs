# Sprint 10 — Prompt Engine

**Date:** 2026-06-29  
**Branch:** `sprint-10-prompt-engine` (merged into `main`)  
**Commit Hash:** `0c4ee5d` (`0c4ee5d053b226a8a05f176928b8b5073f170d40`)

---

## Files Changed

| File | Change Type | Purpose |
|------|-------------|---------|
| `app/schemas/prompt.py` | Created | Prompt Engine Pydantic validation schemas (`PromptShot`, `PromptResponse`). |
| `app/prompt_engine/prompt_builder.py` | Created | Dynamic prompt builder combining project config, focus character details, and storyboard attributes. |
| `app/api/prompts.py` | Created | Router for Prompt Engine exposing the GET prompts endpoint. |
| `app/main.py` | Modified | Imported and registered `prompts_router`. |
| `notes/Sprint_10.md` | Created | Documentation journal for Sprint 10. |

---

## Prompt Format

### Positive Prompt Composition
The positive prompt is a comma-separated list of visual descriptors:
1. **Art Style & Aspect Ratio:** (e.g. `manhwa style, aspect ratio 9:16`)
2. **Shot properties:** Camera angle and shot type (e.g. `High Angle, Wide shot`)
3. **Scene Details:** Environment/Scene title, camera notes, and narration.
4. **Focus Character Appearance & Clothing:** (e.g. `Z-100 (Protagonist), gender: Non-binary, clothing: Silver space suit`)
5. **Quality modifiers:** Cinematic lighting, high detail, masterpiece.

### Negative Prompt Composition
The negative prompt combines:
1. **Project defaults:** `"low quality, blurry, worst quality, normal quality"`
2. **Focus characters' custom negative prompts:** (e.g. `"human face, organic body"`)
3. **Common quality negatives:** `"extra limbs, bad anatomy, deformed, mutated, disfigured, watermark, text, logo, signature"`

### Suggested Filename
Suggested filenames follow the format:
`scene_{scene_number:03d}_shot_{shot_number:03d}.png` (e.g. `scene_001_shot_001.png`)

---

## Example Response (`GET /scenes/1/prompts`)

```json
{
  "scene_id": 1,
  "scene_title": "Intro Scene",
  "project_id": 1,
  "project_title": "Project Alpha",
  "shots": [
    {
      "shot_number": 1,
      "positive_prompt": "manhwa style, aspect ratio 9:16, High Angle, Wide shot, environment: Intro Scene, camera notes: Pan right, narration: In the beginning..., Z-100 (Protagonist), gender: Non-binary, clothing: Silver space suit, cinematic lighting, high detail, masterpiece",
      "negative_prompt": "low quality, blurry, worst quality, normal quality, human face, organic body, extra limbs, bad anatomy, deformed, mutated, disfigured, watermark, text, logo, signature",
      "image_filename": "scene_001_shot_001.png"
    },
    {
      "shot_number": 2,
      "positive_prompt": "manhwa style, aspect ratio 9:16, Eye Level, Medium shot, environment: Intro Scene, camera notes: Pan right, narration: In the beginning..., Z-100 (Protagonist), gender: Non-binary, clothing: Silver space suit, cinematic lighting, high detail, masterpiece",
      "negative_prompt": "low quality, blurry, worst quality, normal quality, human face, organic body, extra limbs, bad anatomy, deformed, mutated, disfigured, watermark, text, logo, signature",
      "image_filename": "scene_001_shot_002.png"
    },
    {
      "shot_number": 3,
      "positive_prompt": "manhwa style, aspect ratio 9:16, Low Angle, Close-up shot, environment: Intro Scene, camera notes: Pan right, narration: In the beginning..., Z-100 (Protagonist), gender: Non-binary, clothing: Silver space suit, cinematic lighting, high detail, masterpiece",
      "negative_prompt": "low quality, blurry, worst quality, normal quality, human face, organic body, extra limbs, bad anatomy, deformed, mutated, disfigured, watermark, text, logo, signature",
      "image_filename": "scene_001_shot_003.png"
    }
  ]
}
```

---

## Lessons Learned

1. **Structured Prompt Composition:** Building visual prompts deterministically by stitching together multiple optional metadata attributes (role, gender, clothing, hair, etc.) creates high quality visual prompts for image generators.
2. **Reusing Storyboard Logic:** Building the prompt builder directly on top of the dynamic storyboard generator output guarantees alignment between generated shots and prompt-to-image metadata.

---

## Regression Status

All endpoints from Sprints 1-10 are fully verified and passing:
- **Projects:** Management operations and config validation work.
- **Stories & Episodes:** Story/Episode hierarchy holds.
- **Scenes:** Operations function correctly.
- **Blueprint:** compilation and stats work with no regressions.
- **Characters:** Registry creation and mapping to scenes works.
- **Storyboard Generator:** Retrieve dynamic storyboards.
- **Prompt Engine:** Generation of structured visual prompts and suggested filenames.
