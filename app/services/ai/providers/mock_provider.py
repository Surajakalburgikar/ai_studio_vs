"""
Mock AI provider implementation for story generation testing.
"""

import json
from .base_provider import BaseProvider


class MockProvider(BaseProvider):
    """Mock provider for testing the story generation pipeline."""

    def generate(self, prompt: str) -> str:
        """Generate a mock story JSON response.

        Args:
            prompt: The input prompt (ignored in mock).

        Returns:
            A deterministic JSON string representing a complete story.
        """
        story_data = {
            "title": "The Whispering Stone",
            "genre": "Fantasy",
            "summary": "An ancient stone tells of a hidden valley where time stands still.",
            "story_text": (
                "In a quiet village bordered by gray mountains, a girl named Lyra "
                "finds a dark stone that hums with sound. She discovers that the stone "
                "retains the memories of past ages and points the way to a hidden, "
                "timeless valley."
            ),
            "episodes": [
                {
                    "episode_number": 1,
                    "title": "The Discovery",
                    "summary": "Lyra finds the humming stone in the ruins near her home.",
                    "scenes": [
                        {
                            "scene_number": 1,
                            "title": "The Ruins",
                            "narration": "Lyra digs in the crumbling soil, uncovering the obsidian stone.",
                            "camera_notes": "Close-up on her hands lifting the stone from the dirt.",
                            "duration_seconds": 12.5
                        },
                        {
                            "scene_number": 2,
                            "title": "The Whisper",
                            "narration": "A soft voice murmurs ancient words directly into Lyra's mind.",
                            "camera_notes": "Medium shot showing her startled expression under the twilight sky.",
                            "duration_seconds": 15.0
                        }
                    ]
                },
                {
                    "episode_number": 2,
                    "title": "The Journey Begins",
                    "summary": "Lyra decides to leave the village and seek the valley.",
                    "scenes": [
                        {
                            "scene_number": 1,
                            "title": "The Mountain Pass",
                            "narration": "She begins her steep ascent into the gray mountain peaks.",
                            "camera_notes": "Wide angle establishing shot of the rugged terrain.",
                            "duration_seconds": 20.0
                        }
                    ]
                }
            ]
        }
        return json.dumps(story_data)
