# AI Services Scaffolding — Sprint 19 Preparation

**Date:** 2026-06-30  
**Repository:** AI_STUDIO  
**Objective:** Scaffold AI service classes and prompt templates under the main backend project directory (`AI_STUDIO`).

---

## File Structure Tree

```text
c:\Projects\AI_STUDIO\
├── app/
│   ├── prompts/
│   │   ├── character_prompt.txt
│   │   ├── image_prompt.txt
│   │   ├── scene_prompt.txt
│   │   └── story_prompt.txt
│   │
│   └── services/
│       └── ai/
│           ├── __init__.py
│           ├── character_generator.py
│           ├── checkpoint_manager.py
│           ├── image_generator.py
│           ├── prompt_generator.py
│           ├── queue_manager.py
│           └── story_generator.py
```

---

## Created Modules & Responsibilities

### 1. `app/services/ai/`
* **`story_generator.py`**: Interacts with LLM models to generate stories, outlines, and summaries using configurations and template files.
* **`character_generator.py`**: Builds visual character profiles and traits using NLP/LLM analysis on story text.
* **`prompt_generator.py`**: Combines scene narration, camera events, and character visual attributes into positive and negative prompts.
* **`image_generator.py`**: Handles direct image generation requests, wrapping local providers or calling remote endpoints.
* **`checkpoint_manager.py`**: Tracks, loads, and caches diffusion model weights, LoRAs, and VAEs.
* **`queue_manager.py`**: Manages job assignment matching worker capabilities, handles lease expiry, and reschedules dead jobs.

### 2. `app/prompts/`
* **`story_prompt.txt`**: LLM instruction template for story generation.
* **`character_prompt.txt`**: LLM instruction template for character trait parsing.
* **`scene_prompt.txt`**: Storyboard and shot breakdown instruction template.
* **`image_prompt.txt`**: Structured style and quality modifier template for Diffusion models.
