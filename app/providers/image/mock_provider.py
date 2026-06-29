import os
import time
from PIL import Image, ImageDraw

from app.providers.image.base import ImageProvider
from app.providers.image.models import ImageResult


class MockImageProvider(ImageProvider):
    """Mock Image Provider that generates a simple placeholder PNG."""

    def generate_image(self, prompt: str, filename: str) -> ImageResult:
        start_time = time.time()

        # Ensure directory exists automatically
        output_dir = os.path.join("generated", "mock")
        os.makedirs(output_dir, exist_ok=True)

        image_path = os.path.join(output_dir, filename)

        # Create placeholder image (800x600 dark slate background)
        width, height = 800, 600
        img = Image.new("RGB", (width, height), color=(30, 30, 45))
        draw = ImageDraw.Draw(img)

        # Write text to image (uses default PIL font)
        draw.text((40, 50), "AI Studio Mock Image", fill=(255, 255, 255))
        draw.text((40, 100), f"Filename: {filename}", fill=(200, 200, 200))

        # Limit prompt to 100 characters
        prompt_snippet = prompt[:100]
        draw.text((40, 150), f"Prompt: {prompt_snippet}", fill=(150, 150, 150))

        # Save the image
        img.save(image_path, "PNG")

        generation_time = round(time.time() - start_time, 4)

        return ImageResult(
            status="success",
            provider="MockImageProvider",
            image_path=image_path,
            generation_time=generation_time,
            metadata={
                "width": width,
                "height": height,
                "format": "PNG",
                "prompt_length": len(prompt),
            },
        )
