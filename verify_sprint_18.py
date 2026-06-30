"""
verify_sprint_18.py — Sprint 18 Pipeline Verification Script

Prepares a complete test pipeline by creating all required entities
through the AI Studio Backend API.

This script:
    1. Creates a temporary project
    2. Creates a story
    3. Creates an episode
    4. Creates a scene (with narration + camera notes for storyboard)
    5. Creates a character (with full visual description)
    6. Assigns the character to the scene
    7. Verifies storyboard generation
    8. Verifies prompt generation
    9. Creates generation jobs
    10. Prints the created job IDs

This script does NOT:
    - Start the worker
    - Generate images
    - Modify the database schema

Usage:
    1. Start the backend:  uvicorn app.main:app --reload
    2. Run this script:    python verify_sprint_18.py
    3. Start the worker:   python -m worker.main
    4. Watch the worker pick up and process the job
"""

import sys
import requests

# ===========================================
# Configuration
# ===========================================
BACKEND_URL = "http://localhost:8000"
PROVIDER = "mock"  # The image provider the worker will use


def check(label: str, response: requests.Response, expected_status: int = 200) -> dict:
    """Verify API response and return parsed JSON."""
    if response.status_code != expected_status:
        print(f"  FAIL  {label}")
        print(f"        Status: {response.status_code}")
        print(f"        Body:   {response.text[:500]}")
        sys.exit(1)
    data = response.json()
    print(f"  OK    {label}")
    return data


def main():
    print("=" * 60)
    print("Sprint 18 — Pipeline Verification")
    print("=" * 60)

    # ------------------------------------------
    # Step 0: Health Check
    # ------------------------------------------
    print("\n[Step 0] Health Check")
    try:
        resp = requests.get(BACKEND_URL, timeout=5)
        check("Backend reachable", resp, 200)
    except requests.ConnectionError:
        print("  FAIL  Backend not running at", BACKEND_URL)
        print("        Start it with: uvicorn app.main:app --reload")
        sys.exit(1)

    # ------------------------------------------
    # Step 1: Create Project
    # ------------------------------------------
    print("\n[Step 1] Create Project")
    resp = requests.post(f"{BACKEND_URL}/projects/", json={
        "title": "Sprint 18 Test — FLUX Integration",
        "description": "End-to-end test for real FLUX image generation pipeline",
        "video_type": "medium",
        "target_duration_seconds": 60,
        "aspect_ratio": "16:9",
        "language": "English",
        "art_style": "anime",
        "narration_style": "third_person",
        "subtitle_language": "English",
        "voice_gender": "female",
    })
    project = check("Project created", resp, 201)
    project_id = project["id"]
    print(f"        Project ID: {project_id}")

    # ------------------------------------------
    # Step 2: Create Story
    # ------------------------------------------
    print("\n[Step 2] Create Story")
    resp = requests.post(f"{BACKEND_URL}/projects/{project_id}/stories", json={
        "title": "The Last Garden",
        "genre": "Fantasy",
        "summary": "A lone gardener discovers the last enchanted garden in a dying world.",
        "story_text": (
            "In a world where all nature has withered, a young woman named Aria "
            "stumbles upon a hidden garden glowing with ethereal light. The flowers "
            "whisper ancient secrets and the trees hum with forgotten magic. She must "
            "protect this last sanctuary from those who seek to exploit its power."
        ),
    })
    story = check("Story created", resp, 201)
    story_id = story["id"]
    print(f"        Story ID: {story_id}")

    # ------------------------------------------
    # Step 3: Create Episode
    # ------------------------------------------
    print("\n[Step 3] Create Episode")
    resp = requests.post(f"{BACKEND_URL}/stories/{story_id}/episodes", json={
        "episode_number": 1,
        "title": "The Discovery",
        "summary": "Aria discovers the hidden enchanted garden.",
    })
    episode = check("Episode created", resp, 201)
    episode_id = episode["id"]
    print(f"        Episode ID: {episode_id}")

    # ------------------------------------------
    # Step 4: Create Scene
    # ------------------------------------------
    print("\n[Step 4] Create Scene")
    resp = requests.post(f"{BACKEND_URL}/episodes/{episode_id}/scenes", json={
        "scene_number": 1,
        "title": "Entering the Garden",
        "narration": (
            "Aria pushes through the crumbling stone arch. Before her stretches "
            "an impossible garden — luminous flowers swaying without wind, their "
            "petals casting soft light across ancient moss-covered pathways."
        ),
        "camera_notes": "Slow dolly forward through the stone arch, revealing the garden in a wide establishing shot",
        "duration_seconds": 8.0,
    })
    scene = check("Scene created", resp, 201)
    scene_id = scene["id"]
    print(f"        Scene ID: {scene_id}")

    # ------------------------------------------
    # Step 5: Create Character
    # ------------------------------------------
    print("\n[Step 5] Create Character")
    resp = requests.post(f"{BACKEND_URL}/stories/{story_id}/characters", json={
        "name": "Aria",
        "role": "protagonist",
        "gender": "female",
        "age": "22",
        "species": "human",
        "description": "A brave young woman who discovers the last enchanted garden",
        "height_cm": 165,
        "body_type": "slender",
        "hair_color": "silver-white",
        "hair_style": "long flowing hair with small braids",
        "eye_color": "emerald green",
        "skin_tone": "fair with a warm glow",
        "face_description": "soft oval face with high cheekbones and determined eyes",
        "clothing": "a tattered earth-tone cloak over a simple linen dress, worn leather boots",
        "accessories": "a small crystal pendant around her neck, a satchel at her side",
        "personality": "curious, brave, compassionate",
        "negative_prompt": "blurry, deformed, extra fingers, bad anatomy, watermark, signature",
    })
    character = check("Character created", resp, 201)
    character_id = character["id"]
    print(f"        Character ID: {character_id}")

    # ------------------------------------------
    # Step 6: Assign Character to Scene
    # ------------------------------------------
    print("\n[Step 6] Assign Character to Scene")
    resp = requests.post(
        f"{BACKEND_URL}/scenes/{scene_id}/characters/{character_id}"
    )
    assignment = check("Character assigned to scene", resp, 201)
    print(f"        Assignment: Scene {scene_id} <-> Character {character_id}")

    # ------------------------------------------
    # Step 7: Verify Storyboard
    # ------------------------------------------
    print("\n[Step 7] Verify Storyboard Generation")
    resp = requests.get(f"{BACKEND_URL}/scenes/{scene_id}/storyboard")
    storyboard = check("Storyboard generated", resp, 200)
    shot_count = len(storyboard.get("shots", []))
    print(f"        Shots generated: {shot_count}")
    for shot in storyboard.get("shots", []):
        print(f"          Shot {shot['shot_number']}: {shot['shot_type']} | {shot['camera_angle']} | {shot['duration_seconds']}s")

    # ------------------------------------------
    # Step 8: Verify Prompts
    # ------------------------------------------
    print("\n[Step 8] Verify Prompt Generation")
    resp = requests.get(f"{BACKEND_URL}/scenes/{scene_id}/prompts")
    prompts = check("Prompts generated", resp, 200)
    for shot in prompts.get("shots", []):
        print(f"          Shot {shot['shot_number']}:")
        print(f"            Positive: {shot['positive_prompt'][:100]}...")
        print(f"            Negative: {shot['negative_prompt'][:80]}...")
        print(f"            Filename: {shot['image_filename']}")

    # ------------------------------------------
    # Step 9: Create Generation Jobs
    # ------------------------------------------
    print("\n[Step 9] Create Generation Jobs")
    resp = requests.post(f"{BACKEND_URL}/jobs", json={
        "scene_id": scene_id,
        "provider": PROVIDER,
        "priority": 0,
    })
    jobs = check("Generation jobs created", resp, 201)
    print(f"        Jobs created: {len(jobs)}")
    print()

    # ------------------------------------------
    # Summary
    # ------------------------------------------
    print("=" * 60)
    print("PIPELINE READY")
    print("=" * 60)
    print()
    print(f"  Project ID:   {project_id}")
    print(f"  Story ID:     {story_id}")
    print(f"  Episode ID:   {episode_id}")
    print(f"  Scene ID:     {scene_id}")
    print(f"  Character ID: {character_id}")
    print(f"  Provider:     {PROVIDER}")
    print()
    print("  Created Jobs:")
    for job in jobs:
        print(f"    Job {job['id']}: shot {job['shot_number']} | {job['status']} | {job['filename']}")
    print()
    print("=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print()
    print("  1. Start the worker:")
    print("       cd C:\\Projects\\AI_STUDIO_WORKER")
    print("       python -m worker.main")
    print()
    print("  2. Watch the worker:")
    print("       - Pick up the job from /jobs/next")
    print("       - Generate a real FLUX image")
    print("       - Save it to generated/")
    print("       - Report completion to backend")
    print()
    print("  3. Verify completion:")
    print(f"       GET {BACKEND_URL}/jobs")
    print(f"       Check that job status = 'completed'")
    print()


if __name__ == "__main__":
    main()
