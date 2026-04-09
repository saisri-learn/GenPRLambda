"""Configuration settings for the Lambda function."""

import os
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # GitHub Configuration
    github_token: str = Field(..., description="GitHub Personal Access Token")
    github_owner: str = Field(..., description="GitHub repository owner")
    github_repo: str = Field(..., description="GitHub repository name")
    default_base_branch: str = Field(default="main", description="Default base branch")

    # LLM Configuration
    llm_provider: Literal["anthropic", "openai"] = Field(
        default="anthropic", description="LLM provider to use"
    )
    llm_model: str = Field(
        default="claude-3-5-sonnet-20241022", description="LLM model identifier"
    )
    llm_api_key: str = Field(..., description="API key for LLM provider")
    llm_temperature: float = Field(default=0.0, description="Temperature for LLM generation")
    llm_max_tokens: int = Field(default=4000, description="Maximum tokens for LLM response")

    # Lambda Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    timeout_buffer: int = Field(
        default=30, description="Seconds before timeout to gracefully stop"
    )

    @property
    def github_repo_url(self) -> str:
        """Get the full GitHub repository URL."""
        return f"https://github.com/{self.github_owner}/{self.github_repo}"

    def validate_required_fields(self) -> None:
        """Validate that all required fields are set."""
        required_fields = {
            "github_token": self.github_token,
            "github_owner": self.github_owner,
            "github_repo": self.github_repo,
            "llm_api_key": self.llm_api_key,
        }

        missing = [field for field, value in required_fields.items() if not value]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.validate_required_fields()
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance (useful for testing)."""
    global _settings
    _settings = None
