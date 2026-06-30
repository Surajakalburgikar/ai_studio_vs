"""
Story Generation Pipeline that encapsulates the orchestrating steps.
"""

import logging
from sqlalchemy.orm import Session
from app.services.ai.exceptions import StoryGenerationError
from app.services.ai.providers.base_provider import BaseProvider
from app.services.ai.parsers.story_parser import StoryParser
from app.services.ai.validators.story_validator import StoryValidator
from app.services.ai.repositories.story_repository import StoryRepository
from app.models.story import Story

logger = logging.getLogger("ai_studio")


class StoryPipeline:
    """Orchestrates the lifecycle of story generation from prompt construction to DB persistence."""

    def __init__(
        self,
        provider: BaseProvider,
        parser: StoryParser,
        validator: StoryValidator,
        repository: StoryRepository
    ) -> None:
        self.provider = provider
        self.parser = parser
        self.validator = validator
        self.repository = repository

    def execute(self, project_id: int, formatted_prompt: str) -> Story:
        """Run the full story generation pipeline.

        Args:
            project_id: The ID of the project the story is created under.
            formatted_prompt: The template-injected prompt ready for the AI model.

        Returns:
            The persisted Story SQLAlchemy model.

        Raises:
            StoryGenerationError: If any pipeline step fails.
        """
        # Step 1: Execute AI Provider
        logger.info(f"Invoking AI provider '{type(self.provider).__name__}' for story generation...")
        try:
            raw_response = self.provider.generate(formatted_prompt)
            logger.info("AI provider returned a response successfully.")
        except Exception as e:
            logger.error(f"AI Provider failed: {e}")
            raise StoryGenerationError(f"AI generation failed: {str(e)}") from e

        # Step 2: Parse Raw Output
        logger.info("Parsing raw AI response...")
        parsed_data = self.parser.parse(raw_response)

        # Step 3: Validate Story Structure
        logger.info("Validating parsed story...")
        self.validator.validate(parsed_data)

        # Step 4: Persist in Database
        logger.info("Persisting story hierarchy to database...")
        story = self.repository.save_story(project_id, parsed_data)

        return story
