"""
Abstract base class for all story generation AI providers.
"""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Abstract base class for all AI story providers."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a story narrative/JSON response from the given prompt.

        Args:
            prompt: Formatted prompt containing context and structural instructions.

        Returns:
            Raw response text from the AI provider.

        Raises:
            ProviderError: If the generation fails.
        """
        pass
