"""
Gemini AI provider implementation for story generation.
"""

from .base_provider import BaseProvider


class GeminiProvider(BaseProvider):
    """Gemini provider for AI story generation.

    Currently not implemented (for Sprint 21 integration).
    """

    def generate(self, prompt: str) -> str:
        """Generate a story using the Gemini API.

        Raises:
            NotImplementedError: As this provider is not implemented yet.
        """
        raise NotImplementedError("GeminiProvider is not implemented yet. Use 'mock' provider.")
