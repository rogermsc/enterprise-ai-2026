"""Configuration management for the Gateway.

Uses pydantic-settings for type-safe configuration with environment variable support.
Follows 12-factor app principles for configuration management.
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="GOODAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    enable_docs: bool = Field(default=True, description="Enable API documentation")

    # Security
    secret_key: str = Field(default="change-me-in-production", description="JWT secret key")
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiry_hours: int = Field(default=24, description="JWT token expiry in hours")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins",
    )

    # Rate Limiting
    rate_limit_requests: int = Field(default=100, description="Requests per window")
    rate_limit_window_seconds: int = Field(default=60, description="Rate limit window")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/goodai",
        description="Database connection URL",
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # LLM
    openai_api_key: str = Field(default="", description="OpenAI API key")
    default_model: str = Field(default="gpt-4-turbo-preview", description="Default LLM model")
    max_tokens: int = Field(default=4096, description="Max tokens per request")

    # Observability
    otel_endpoint: str = Field(default="", description="OpenTelemetry collector endpoint")
    log_level: str = Field(default="INFO", description="Logging level")

    # Feature Flags
    enable_human_in_loop: bool = Field(default=True, description="Enable human-in-the-loop")
    enable_tool_sandboxing: bool = Field(default=True, description="Enable tool sandboxing")
    max_agent_iterations: int = Field(default=10, description="Max agent reasoning iterations")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
