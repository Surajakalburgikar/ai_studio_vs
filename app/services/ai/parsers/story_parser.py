"""
Story parser to extract and structure raw AI responses.
"""

import json
import logging
import re
from typing import Dict, Any
from app.services.ai.exceptions import ParserError

logger = logging.getLogger("ai_studio")


class StoryParser:
    """Parses raw text outputs from AI providers into structured Python dictionaries."""

    def parse(self, raw_text: str) -> Dict[str, Any]:
        """Extract and parse a JSON object from raw response text.

        Handles markdown code fences if present.

        Args:
            raw_text: Raw string returned by the LLM.

        Returns:
            Parsed dictionary representing the story structure.

        Raises:
            ParserError: If the content is not valid JSON or lacks required structure.
        """
        if not raw_text or not raw_text.strip():
            logger.error("Raw text response is empty")
            raise ParserError("Empty response received from AI provider")

        cleaned = raw_text.strip()

        # Handle markdown code fences (```json ... ``` or ``` ... ```)
        if "```" in cleaned:
            # Match anything between ```json and ``` or ``` and ```
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()
            else:
                # Fallback: remove backticks
                cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(cleaned)
            if not isinstance(data, dict):
                logger.error("Parsed JSON is not a dictionary")
                raise ParserError("AI response did not parse into a JSON object/dictionary")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode failed: {e}. Raw content: {raw_text[:200]}")
            raise ParserError(f"Failed to parse AI response as valid JSON: {str(e)}")
