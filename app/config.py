"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Central configuration for the DocProcessing application."""

    # OpenAI
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4.1", description="Primary LLM model for Pipeline A")
    pipeline_b_fallback_model: str = Field(
        default="gpt-4.1-mini", description="Fallback LLM model for Pipeline B"
    )

    # Processing
    min_confidence: float = Field(default=0.6, description="Minimum confidence threshold")
    allow_leading_zero_equiv: bool = Field(
        default=True, description="Allow leading-zero equivalence in PO matching"
    )

    # Storage
    storage_base_path: str = Field(default="data/", description="Base path for file storage")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")

    # API
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}


# Singleton instance
settings = Settings()
