from abc import ABC, abstractmethod
from app.providers.image.models import ImageResult


class ImageProvider(ABC):
    """Abstract base class representing an image generation provider."""

    @abstractmethod
    def generate_image(self, prompt: str, filename: str) -> ImageResult:
        """Generate an image based on a text prompt and save it to the specified filename."""
        pass
