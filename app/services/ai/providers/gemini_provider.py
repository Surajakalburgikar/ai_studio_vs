"""
Gemini AI provider implementation for story generation.
"""

import logging
import socket
import time
from google import genai
from google.genai import types
from google.genai.errors import APIError
import httpx

from app.core.config import settings
from app.services.ai.exceptions import ProviderError
from .base_provider import BaseProvider

logger = logging.getLogger("ai_studio")


class GeminiProvider(BaseProvider):
    """Gemini provider for AI story generation using the official google-genai SDK."""

    def __init__(self) -> None:
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            logger.error("GEMINI_API_KEY is not configured in settings.")
            raise ProviderError("Gemini API key is missing. Please set GEMINI_API_KEY in .env.")
        
        try:
            self.client = genai.Client(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client: {e}")
            raise ProviderError(f"Failed to initialize Gemini Client: {str(e)}") from e

    def generate(self, prompt: str) -> str:
        """Generate a story using the Gemini API with structured JSON output and retry logic.

        Args:
            prompt: Formatted prompt containing context and structural instructions.

        Returns:
            Raw response text (JSON string) from Gemini.

        Raises:
            ProviderError: If the generation fails after retries.
        """
        logger.info(f"GeminiProvider selected. Starting story generation with model: '{settings.GEMINI_MODEL}'")
        
        # Load hyperparameters from config
        temperature = settings.GEMINI_TEMPERATURE
        top_p = settings.GEMINI_TOP_P
        top_k = settings.GEMINI_TOP_K
        
        config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            response_mime_type="application/json"
        )

        max_retries = 3
        delay = 1.0  # Initial delay in seconds for exponential backoff

        for attempt in range(1, max_retries + 2):  # Try up to 4 times (1 original + 3 retries)
            try:
                t0 = time.perf_counter()
                logger.info(f"Sending prompt to Gemini (Attempt {attempt}/{max_retries + 1})...")
                
                response = self.client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config=config
                )
                
                latency_ms = (time.perf_counter() - t0) * 1000
                logger.info(f"Gemini generation completed in {latency_ms:.2f}ms on attempt {attempt}.")

                # Log token usage if available
                if response.usage_metadata:
                    prompt_tokens = response.usage_metadata.prompt_token_count
                    response_tokens = response.usage_metadata.candidates_token_count
                    total_tokens = response.usage_metadata.total_token_count
                    logger.info(
                        f"Gemini Token Usage - Prompt: {prompt_tokens}, "
                        f"Response: {response_tokens}, Total: {total_tokens}"
                    )

                if not response.text:
                    logger.warning("Gemini returned an empty text response.")
                    raise ProviderError("Gemini returned an empty response.")

                return response.text

            except (APIError, httpx.HTTPError, socket.error, TimeoutError) as e:
                is_retryable = True
                error_message = str(e)
                
                if isinstance(e, APIError):
                    # APIError contains the HTTP status code
                    # Retry on 429 (rate limit) or 5xx (server error)
                    if e.code not in (429, 500, 502, 503, 504):
                        is_retryable = False
                
                # Check if we should log failure or retry
                if attempt > max_retries or not is_retryable:
                    logger.error(
                        f"Gemini Provider failed permanently on attempt {attempt}. "
                        f"Retryable: {is_retryable}. Error: {error_message}"
                    )
                    raise ProviderError(f"Gemini generation failed: {error_message}") from e
                
                # Log retry warning
                logger.warning(
                    f"Gemini Provider temporary failure on attempt {attempt}: {error_message}. "
                    f"Retrying in {delay} seconds..."
                )
                time.sleep(delay)
                delay *= 2.0  # Exponential backoff

            except Exception as e:
                # Catch any unexpected SDK/connection issues and wrap them
                logger.error(f"Unexpected error in Gemini Provider on attempt {attempt}: {e}")
                raise ProviderError(f"Unexpected error during Gemini generation: {str(e)}") from e
