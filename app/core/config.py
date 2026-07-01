from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    PROJECT_NAME: str = "AI Studio API"
    VERSION: str = "0.1.0"
    DATABASE_URL: str = "sqlite:///./ai_studio.db"
    ALLOWED_ORIGINS: list[str] = ["*"]
    STORY_GENERATOR_PROVIDER: str = "mock"
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.2
    GEMINI_TOP_P: float = 0.95
    GEMINI_TOP_K: int = 40
    GEMINI_MODEL_PRIORITY: str = "gemini-2.5-flash,gemini-3.5-flash,gemini-3-flash,gemini-3.1-flash-lite,gemini-2.5-flash-lite"
    GEMINI_MODEL_COOLDOWN_MINUTES: int = 60

    PIPELINE_MODE: str = "development"
    ALLOW_QUALITY_DOWNGRADE: bool = False
    PREFERRED_MODEL_PROFILE: dict = {}
    PREFERRED_PROVIDER_PROFILE: dict = {}
    CHECKPOINT_INTERVAL: int = 1
    CONTINUITY_EXPORT_PATH: str = "./continuity"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    from pydantic import model_validator
    @model_validator(mode="after")
    def validate_gemini_config(self) -> "Settings":
        if self.STORY_GENERATOR_PROVIDER == "gemini" and not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY must be set when STORY_GENERATOR_PROVIDER is 'gemini'")
        return self


settings = Settings()
