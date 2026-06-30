"""
Story Generator Service.

Orchestrates the prompt building, AI model invocation, parsing, validation,
and database persistence using the StoryPipeline.
"""

import logging
from pathlib import Path
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.story import Story
from app.services.ai.exceptions import StoryGenerationError, ValidationError
from app.services.ai.providers.base_provider import BaseProvider
from app.services.ai.providers.gemini_provider import GeminiProvider
from app.services.ai.providers.mock_provider import MockProvider
from app.services.ai.parsers.story_parser import StoryParser
from app.services.ai.validators.story_validator import StoryValidator
from app.services.ai.repositories.story_repository import StoryRepository
from app.services.ai.pipeline.story_pipeline import StoryPipeline

logger = logging.getLogger("ai_studio")


class StoryGenerator:
    """Production service class orchestrating the AI story generation pipeline."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.provider = self._resolve_provider()
        self.parser = StoryParser()
        self.validator = StoryValidator()
        self.repository = StoryRepository(self.db)

        # Instantiate pipeline coordinator
        self.pipeline = StoryPipeline(
            provider=self.provider,
            parser=self.parser,
            validator=self.validator,
            repository=self.repository
        )

    def _resolve_provider(self) -> BaseProvider:
        """Resolve and instantiate the configured AI story provider.

        Reads STORY_GENERATOR_PROVIDER from settings.
        Supported providers: 'mock', 'gemini'.
        """
        provider_name = getattr(settings, "STORY_GENERATOR_PROVIDER", "mock").lower()
        logger.info(f"Resolving AI Story Provider for: '{provider_name}'")

        if provider_name == "mock":
            return MockProvider()
        elif provider_name == "gemini":
            return GeminiProvider()
        else:
            logger.error(f"Unsupported story provider name: '{provider_name}'")
            raise StoryGenerationError(f"Unsupported story generator provider: '{provider_name}'")

    def _load_prompt_template(self) -> str:
        """Load prompt template from the configured story_prompt.txt path."""
        # Locate c:\Projects\AI_STUDIO\app\prompts\story_prompt.txt relative to this file
        template_path = Path(__file__).resolve().parents[3] / "prompts" / "story_prompt.txt"
        logger.info(f"Loading story prompt template from: {template_path}")

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info("Prompt template loaded successfully.")
            return content
        except Exception as e:
            logger.error(f"Failed to read prompt template at {template_path}: {e}")
            raise StoryGenerationError(f"Failed to load story prompt template: {str(e)}")

    def generate(self, project_id: int, variables: Dict[str, Any]) -> Story:
        """Execute story generation pipeline using the given variables.

        Args:
            project_id: Project identifier to link the generated story to.
            variables: Variables to inject into the prompt template.
                Expected keys: genre, theme, art_style, audience, language,
                target_duration, episode_count, episode_duration.

        Returns:
            The created and persisted Story object.

        Raises:
            StoryGenerationError: If any pipeline step fails.
        """
        logger.info(f"Starting story generation for Project ID: {project_id}")

        # 1. Load template
        template = self._load_prompt_template()

        # 2. Prepare prompt variables
        required_vars = [
            "genre", "target_duration", "audience", "language",
            "art_style", "episode_count", "episode_duration", "theme"
        ]

        missing_vars = [var for var in required_vars if var not in variables]
        if missing_vars:
            logger.error(f"Missing required prompt variables: {missing_vars}")
            raise ValidationError(f"Missing required prompt variables: {', '.join(missing_vars)}")

        try:
            formatted_prompt = template.format(
                genre=variables["genre"],
                target_duration=variables["target_duration"],
                audience=variables["audience"],
                language=variables["language"],
                art_style=variables["art_style"],
                episode_count=variables["episode_count"],
                episode_duration=variables["episode_duration"],
                theme=variables["theme"]
            )
            logger.info("Prompt variables injected successfully.")
        except KeyError as e:
            logger.error(f"Formatting failed due to unknown key: {e}")
            raise StoryGenerationError(f"Formatting prompt template failed: {str(e)}")

        # 3. Delegate execution to pipeline
        try:
            story = self.pipeline.execute(project_id, formatted_prompt)
            logger.info(f"Story generation completed successfully for project {project_id}.")
            return story
        except StoryGenerationError:
            # Re-raise domain exceptions directly
            raise
        except Exception as e:
            logger.error(f"Unexpected error in generation pipeline: {e}")
            raise StoryGenerationError(f"Unexpected error in story generation: {str(e)}")
