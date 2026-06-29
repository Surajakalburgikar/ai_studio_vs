from app.providers.image.base import ImageProvider
from app.providers.image.models import ImageResult
from app.providers.image.mock_provider import MockImageProvider


class ImageProviderManager:
    """Manager class to switch active image providers and run image generation tasks."""

    def __init__(self, default_provider: ImageProvider = None):
        self._provider = default_provider or MockImageProvider()

    def set_provider(self, provider: ImageProvider) -> None:
        """Set the active image provider."""
        self._provider = provider

    def generate(self, prompt: str, filename: str) -> ImageResult:
        """Delegate image generation to the active provider."""
        return self._provider.generate_image(prompt, filename)
