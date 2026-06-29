from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    PROJECT_NAME: str = "AI Studio API"
    VERSION: str = "0.1.0"
    DATABASE_URL: str = "sqlite:///./ai_studio.db"
    ALLOWED_ORIGINS: list[str] = ["*"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
