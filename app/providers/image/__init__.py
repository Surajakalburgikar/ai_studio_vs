from app.providers.image.base import ImageProvider
from app.providers.image.models import ImageResult
from app.providers.image.mock_provider import MockImageProvider
from app.providers.image.manager import ImageProviderManager

image_provider_manager = ImageProviderManager()

__all__ = [
    "ImageProvider",
    "ImageResult",
    "MockImageProvider",
    "ImageProviderManager",
    "image_provider_manager",
]
