"""
Domain-specific exceptions for the AI Story Generation Pipeline.
"""

class StoryGenerationError(Exception):
    """Base exception for all story generation pipeline errors."""
    pass


class ProviderError(StoryGenerationError):
    """Raised when the AI provider (Gemini, Mock, etc.) fails to execute or returns an error."""
    pass


class ParserError(StoryGenerationError):
    """Raised when the raw AI response cannot be parsed into valid JSON or structural format."""
    pass


class ValidationError(StoryGenerationError):
    """Raised when the parsed story does not meet structural or business rules validation."""
    pass


class RepositoryError(StoryGenerationError):
    """Raised when saving the story, episodes, or scenes to the database fails."""
    pass


class QualityPolicyPauseException(StoryGenerationError):
    """Raised when a quality policy violation occurs and the run must be paused."""
    pass
