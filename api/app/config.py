"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All config is read from environment variables (or a .env file)."""

    database_url: str = "postgresql://localhost:5432/bizlens"
    internal_api_key: str = "bizlens_internal_secret_key_2025"
    cors_origins: str = "http://localhost:3000"

    # AI Keys
    gemini_api_key: str = ""
    anthropic_api_key: str = ""

    # Blob
    blob_read_write_token: str = ""

    # Rate limiting (requests per minute)
    rate_limit_chat: int = 10
    rate_limit_reports: int = 5

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()  # type: ignore[call-arg]
