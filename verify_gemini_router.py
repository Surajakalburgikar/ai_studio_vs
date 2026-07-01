import unittest
from unittest.mock import MagicMock, patch
import time
import socket
import httpx
from google.genai.errors import APIError

from app.core.config import settings
from app.services.ai.exceptions import ProviderError
from app.services.ai.providers.gemini_provider import GeminiProvider
from app.services.ai.providers.gemini_model_router import GeminiModelRouter, _cooldowns


class MockUsageMetadata:
    def __init__(self):
        self.prompt_token_count = 10
        self.candidates_token_count = 20
        self.total_token_count = 30


class MockResponse:
    def __init__(self, text):
        self.text = text
        self.usage_metadata = MockUsageMetadata()


class TestGeminiModelRouter(unittest.TestCase):

    def setUp(self):
        # Reset the shared cooldown state before each test
        _cooldowns.clear()
        
        # Override config variables to ensure predictable values
        self.original_priority = settings.GEMINI_MODEL_PRIORITY
        self.original_cooldown = settings.GEMINI_MODEL_COOLDOWN_MINUTES
        self.original_api_key = settings.GEMINI_API_KEY
        
        settings.GEMINI_MODEL_PRIORITY = "gemini-2.5-flash,gemini-3.5-flash,gemini-3-flash,gemini-3.1-flash-lite,gemini-2.5-flash-lite"
        settings.GEMINI_MODEL_COOLDOWN_MINUTES = 60
        settings.GEMINI_API_KEY = "test_key_present"

    def tearDown(self):
        settings.GEMINI_MODEL_PRIORITY = self.original_priority
        settings.GEMINI_MODEL_COOLDOWN_MINUTES = self.original_cooldown
        settings.GEMINI_API_KEY = self.original_api_key

    def test_priority_ordering(self):
        router = GeminiModelRouter()
        priority_list = router.get_priority_list()
        self.assertEqual(
            priority_list,
            ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-3-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]
        )
        self.assertEqual(router.get_active_model(), "gemini-2.5-flash")

    @patch("google.genai.Client")
    def test_primary_model_success(self, mock_client_class):
        # Mock Client setup
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value = MockResponse('{"story": "success"}')
        
        provider = GeminiProvider()
        result = provider.generate("Write a story")
        
        self.assertEqual(result, '{"story": "success"}')
        # Check that it called generate_content with the primary model
        mock_client.models.generate_content.assert_called_once()
        args, kwargs = mock_client.models.generate_content.call_args
        self.assertEqual(kwargs["model"], "gemini-2.5-flash")

    @patch("google.genai.Client")
    def test_primary_model_quota_exhausted(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Primary fails with 429 Quota Exhausted, secondary succeeds
        def side_effect(*args, **kwargs):
            if kwargs["model"] == "gemini-2.5-flash":
                raise APIError(code=429, response_json={"error": {"message": "Quota exhausted"}})
            return MockResponse('{"story": "secondary success"}')
            
        mock_client.models.generate_content.side_effect = side_effect
        
        provider = GeminiProvider()
        result = provider.generate("Write a story")
        
        self.assertEqual(result, '{"story": "secondary success"}')
        # Verify first model is now in cooldown
        router = GeminiModelRouter()
        self.assertFalse(router.is_model_available("gemini-2.5-flash"))
        self.assertTrue(router.is_model_available("gemini-3.5-flash"))
        self.assertEqual(router.get_active_model(), "gemini-3.5-flash")

    @patch("google.genai.Client")
    def test_primary_model_429(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Primary fails with 429, secondary succeeds
        def side_effect(*args, **kwargs):
            if kwargs["model"] == "gemini-2.5-flash":
                raise APIError(code=429, response_json={"error": {"message": "Resource has been exhausted (e.g. queries per minute)"}})
            return MockResponse('{"story": "secondary success"}')
            
        mock_client.models.generate_content.side_effect = side_effect
        
        provider = GeminiProvider()
        result = provider.generate("Write a story")
        
        self.assertEqual(result, '{"story": "secondary success"}')
        router = GeminiModelRouter()
        self.assertFalse(router.is_model_available("gemini-2.5-flash"))

    @patch("google.genai.Client")
    def test_primary_model_timeout(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        def side_effect(*args, **kwargs):
            if kwargs["model"] == "gemini-2.5-flash":
                raise TimeoutError("Connection timed out")
            return MockResponse('{"story": "secondary success"}')
            
        mock_client.models.generate_content.side_effect = side_effect
        
        provider = GeminiProvider()
        result = provider.generate("Write a story")
        
        self.assertEqual(result, '{"story": "secondary success"}')
        router = GeminiModelRouter()
        self.assertFalse(router.is_model_available("gemini-2.5-flash"))

    @patch("google.genai.Client")
    def test_primary_model_invalid_api_key(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Invalid API key error (e.g. 403 or 401)
        mock_client.models.generate_content.side_effect = APIError(
            code=403, response_json={"error": {"message": "API key not valid"}}
        )
        
        provider = GeminiProvider()
        with self.assertRaises(ProviderError) as context:
            provider.generate("Write a story")
            
        self.assertIn("API key", str(context.exception))
        # Verify it did not cooldown the model because it was a permanent/auth error
        router = GeminiModelRouter()
        self.assertTrue(router.is_model_available("gemini-2.5-flash"))

    def test_cooldown_behavior(self):
        router = GeminiModelRouter()
        self.assertTrue(router.is_model_available("gemini-2.5-flash"))
        
        router.mark_unavailable("gemini-2.5-flash")
        self.assertFalse(router.is_model_available("gemini-2.5-flash"))
        self.assertEqual(router.get_active_model(), "gemini-3.5-flash")

    def test_recovery_after_cooldown_expires(self):
        router = GeminiModelRouter()
        
        # Mark model unavailable for 60 minutes
        router.mark_unavailable("gemini-2.5-flash", cooldown_minutes=60)
        self.assertFalse(router.is_model_available("gemini-2.5-flash"))
        
        # Mock time forward by 61 minutes
        current_time = time.time()
        with patch("time.time", return_value=current_time + (61 * 60)):
            self.assertTrue(router.is_model_available("gemini-2.5-flash"))
            self.assertEqual(router.get_active_model(), "gemini-2.5-flash")


if __name__ == "__main__":
    unittest.main()
