"""
Gemini AI provider implementation for story generation with failover, routing, and project model pinning.
"""

import logging
import socket
import time
import inspect
from google import genai
from google.genai import types
from google.genai.errors import APIError
import httpx

from app.core.config import settings
from app.services.ai.exceptions import ProviderError
from .base_provider import BaseProvider
from .gemini_model_router import GeminiModelRouter
from app.database.session import SessionLocal
from app.models.project import Project

logger = logging.getLogger("ai_studio")


def find_project_id_in_stack() -> int | None:
    """Inspects the calling stack to find the project_id parameter."""
    for frame_info in inspect.stack():
        function_name = frame_info.function
        if function_name in ("execute", "generate"):
            frame_locals = frame_info.frame.f_locals
            if "project_id" in frame_locals:
                return frame_locals["project_id"]
    return None


class GeminiProvider(BaseProvider):
    """Gemini provider for AI story generation using the official google-genai SDK."""

    def __init__(self) -> None:
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            logger.error("GEMINI_API_KEY is not configured in settings.")
            raise ProviderError("Gemini API key is missing. Please set GEMINI_API_KEY in .env.")
        
        try:
            self.client = genai.Client(api_key=api_key)
            self.router = GeminiModelRouter()
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client: {e}")
            raise ProviderError(f"Failed to initialize Gemini Client: {str(e)}") from e

    def _classify_error(self, e: Exception) -> tuple[bool, str]:
        """Classify if the error is retryable (triggers failover) or permanent.
        
        Returns:
            (should_failover, reason_string)
        """
        error_msg = str(e).lower()
        
        # Check APIError code if present
        if hasattr(e, "code") and getattr(e, "code") is not None:
            code = getattr(e, "code")
            if code == 429:
                return True, "Rate limited / Quota exhausted (429)"
            if code >= 500:
                return True, f"Temporary service unavailable ({code})"
            if code in (400, 401, 403, 404):
                if any(term in error_msg for term in ["invalid api key", "invalid key", "unauthorized", "api key not", "forbidden"]):
                    return False, "Invalid API key / Unauthorized"
                if any(term in error_msg for term in ["invalid prompt", "invalid request", "bad request"]):
                    return False, "Invalid prompt / Bad request"
                return False, f"Permanent request error ({code})"
        
        # Check for invalid prompt/key/request specifically in the message
        if any(term in error_msg for term in ["invalid api key", "invalid key", "unauthorized", "api key not", "forbidden", "401", "403"]):
            return False, "Invalid API key / Unauthorized"
            
        if any(term in error_msg for term in ["invalid prompt", "invalid request", "bad request", "400"]):
            return False, "Invalid prompt / Bad request"

        # Check for timeout exceptions
        if isinstance(e, (TimeoutError, socket.timeout)) or "timeout" in error_msg or "timed out" in error_msg:
            return True, "Network timeout"
            
        if "503" in error_msg or "502" in error_msg or "500" in error_msg or "service unavailable" in error_msg or "temporary" in error_msg:
            return True, "Temporary service unavailable"

        # Check for rate limits / quota exhausted in the message text
        if any(term in error_msg for term in ["rate limit", "quota", "exhausted", "limit exceeded", "429"]):
            return True, "Rate limit / Quota exceeded"

        # Check for general network exceptions
        if isinstance(e, (httpx.HTTPError, socket.error)):
            return True, "Network connection error"

        # If it's a ProviderError raised from empty response
        if isinstance(e, ProviderError):
            return True, "Empty response or provider failure"

        # By default, treat unknown/unexpected exception as permanent to avoid infinite loops on syntax/code errors
        return False, "Unexpected internal/permanent error"

    def generate(self, prompt: str) -> str:
        """Generate a story using the Gemini API, routing dynamically across available models.

        Args:
            prompt: Formatted prompt containing context and structural instructions.

        Returns:
            Raw response text (JSON string) from Gemini.

        Raises:
            ProviderError: If the generation fails or no models are available.
        """
        temperature = settings.GEMINI_TEMPERATURE
        top_p = settings.GEMINI_TOP_P
        top_k = settings.GEMINI_TOP_K
        
        config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            response_mime_type="application/json"
        )

        last_failure_reason = None
        attempted_models = []

        # Find project and its preferred model
        project_id = find_project_id_in_stack()
        preferred_model = None
        if project_id:
            db = SessionLocal()
            try:
                project = db.query(Project).filter(Project.id == project_id).first()
                if project and project.preferred_story_model:
                    preferred_model = project.preferred_story_model
                    logger.info(f"[Gemini Router] Found preferred model '{preferred_model}' for project {project_id}.")
            except Exception as ex:
                logger.error(f"[Gemini Router] Error querying preferred model for project {project_id}: {ex}")
            finally:
                db.close()
        
        while True:
            active_model = None
            selection_reason = None

            # Attempt preferred model first if configured and not yet tried
            if preferred_model and preferred_model not in attempted_models:
                if self.router.is_model_available(preferred_model):
                    active_model = preferred_model
                    selection_reason = "Project Preferred Model"
                else:
                    logger.info(
                        f"[Gemini Router] Project preferred model '{preferred_model}' "
                        "is currently on cooldown. Falling back to router priority."
                    )
            
            # Resolve next model from router if no active model is selected yet
            if not active_model:
                try:
                    priority_list = self.router.get_priority_list()
                    for model in priority_list:
                        if model not in attempted_models and self.router.is_model_available(model):
                            active_model = model
                            break
                    
                    if not active_model:
                        raise ProviderError("All configured Gemini models are currently cooling down.")
                    
                    selection_reason = "Primary model selected" if not last_failure_reason else f"Primary model rate limited ({last_failure_reason})"
                except ProviderError as e:
                    logger.error(f"[Gemini Router] No models available: {e}")
                    raise ProviderError(f"Gemini generation failed: {str(e)}") from e

            logger.info(f"[Gemini Router] Using model: {active_model} Reason: {selection_reason}")
            attempted_models.append(active_model)
            
            # Record request initiation in stats
            self.router.record_request(active_model)
            
            try:
                t0 = time.perf_counter()
                logger.info(f"Sending prompt to Gemini with model '{active_model}'...")
                
                response = self.client.models.generate_content(
                    model=active_model,
                    contents=prompt,
                    config=config
                )
                
                latency_ms = (time.perf_counter() - t0) * 1000
                logger.info(f"Gemini generation completed in {latency_ms:.2f}ms using model '{active_model}'.")

                # Record success in stats and state
                self.router.record_success(active_model, latency_ms)

                # Save successful model to project's preferred_story_model if not already pinned
                if project_id and not preferred_model:
                    db = SessionLocal()
                    try:
                        project = db.query(Project).filter(Project.id == project_id).first()
                        if project and not project.preferred_story_model:
                            project.preferred_story_model = active_model
                            db.commit()
                            logger.info(f"Automatically pinned model '{active_model}' to project {project_id}.")
                            preferred_model = active_model
                    except Exception as ex:
                        logger.error(f"Error pinning preferred model for project {project_id}: {ex}")
                    finally:
                        db.close()

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
                    logger.warning(f"Gemini returned an empty text response for model '{active_model}'.")
                    raise ProviderError("Gemini returned an empty response.")

                return response.text

            except Exception as e:
                should_failover, reason = self._classify_error(e)
                
                # Record failure in stats and state
                self.router.record_failure(active_model, reason)
                
                if not should_failover:
                    logger.error(
                        f"Gemini Provider failed permanently with model '{active_model}'. "
                        f"Error: {e}"
                    )
                    raise ProviderError(f"Gemini generation failed: {str(e)}") from e
                
                # Mark model in cooldown
                self.router.mark_unavailable(active_model)
                
                # Get next model name for logs
                next_model = "None (No models left)"
                priority_list = self.router.get_priority_list()
                for model in priority_list:
                    if model not in attempted_models and self.router.is_model_available(model):
                        next_model = model
                        break
                
                logger.warning(
                    f"[Gemini Router] Failover occurred:\n"
                    f"Old model: {active_model}\n"
                    f"Reason: {reason} ({str(e)})\n"
                    f"New model: {next_model}"
                )
                
                last_failure_reason = reason
                if next_model == "None (No models left)":
                    raise ProviderError(f"Gemini generation failed on all models. Last error: {str(e)}") from e
