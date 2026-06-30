# Roadmap

This document outlines the development trajectory of AI Studio, covering completed foundational work and planned future phases.

## Phase 1: Foundational Structure (Sprints 1–10)
* **Backend Architecture:** Initialize modular FastAPI structure with SQLite, SQLAlchemy, Alembic, and Pydantic schemas.
* **Core Models:** Define Projects, Stories, Episodes, Scenes, and Characters.
* **Database Relationships:** Establish database hierarchies and migration pipelines.
* **Project Management Module:** Add endpoints to create, list, update, and manage story assets.
* **Character Registry:** Build centralized database tracking for character descriptions, visual traits, and reference prompts.

## Phase 2: Orchestration & Mock Worker (Sprints 11–17)
* **Scene Director Foundation:** Introduce a generic `timeline_events` schema to support custom directing plans (camera, character, environment, effects, audio).
* **Prompt Builder Engine:** Dynamically combine character descriptions, scene narration, and storyboard metadata into positive and negative prompts.
* **Worker Service:** Initialize `AI_STUDIO_WORKER` with queue polling (`/jobs/next`) and basic reporter callback structure.
* **Mock Pipeline:** Build a Mock Image Provider producing offline placeholder PNGs to test end-to-end integration without network dependencies.

## Phase 3: Real Integration & Production-Ready Providers (Sprints 18–25)
* **Sprint 18 (Current):** Integrate the real FLUX image generator via the Hugging Face Inference API, preserving the existing abstract provider interface and keeping changes inside `main.py` minimal.
* **Sprint 19 (Upcoming):** Design and implement a dynamic **Provider Registry** to eliminate hardcoded provider mappings in `Executor` and support runtime configuration of multiple backends.
* **Sprint 20:** Implement cloud storage adapters (e.g., Google Drive, AWS S3) using the `BaseStorage` interface.
* **Sprint 21:** Support character consistency mechanisms (e.g., LoRAs, IP-Adapters) and reference image inputs within the generation pipeline.
* **Sprint 22:** Introduce a **Worker Registry** for coordinate distribution of jobs across multiple active GPU instances.

## Phase 4: Video & Animation Pipeline (Sprints 26+)
* **Animation Pipeline:** Extend the generation pipeline from static images to video generation using temporal engines (e.g., ComfyUI, Runway, open-source video models).
* **Audio & Subtitle Synthesizer:** Incorporate text-to-speech (TTS) voice generation and automated subtitle alignment.
* **Production Packaging:** Orchestrate final MP4 video compilation combining visual shots, narration tracks, ambient sound, and overlay subtitles.
