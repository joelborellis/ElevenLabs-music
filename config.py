"""
Centralized application configuration.

Kept in its own module (rather than in ``main.py``) so that service, storage, and
database modules can import ``settings`` without creating an import cycle through
``main`` -> ``routers`` -> ``services``.
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings sourced from environment variables / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra keys in .env that aren't defined here
    )

    # --- App ---
    app_name: str = "fastapi-starter"
    app_version: str = "1.0.0"
    environment: str = "development"

    # --- CORS ---
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8000",
    ]

    # --- OpenTelemetry ---
    otel_enabled: bool = True
    otel_exporter_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "fastapi-app"

    # --- Rendered-music storage ---
    # Which backend serves/stores rendered audio: "local" (filesystem) or "azure".
    storage_backend: str = "local"
    # Azure Blob endpoint, e.g. "https://<account>.blob.core.windows.net".
    # Used with managed identity (DefaultAzureCredential) when no connection string.
    azure_storage_account_url: Optional[str] = None
    # Container that holds rendered audio (created on startup if missing).
    azure_storage_container: str = "music"
    # Optional dev-only fallback: full connection string. If set, it takes
    # precedence over managed identity so local runs work without `az login`.
    azure_storage_connection_string: Optional[str] = None
    # Future toggle: redirect to short-lived SAS URLs instead of proxying bytes.
    storage_signed_urls: bool = False
    # Base directory for the local filesystem backend (dev only).
    local_storage_dir: str = "output/music"

    # --- Metadata database ---
    # SQLAlchemy async URL. Production: Azure Database for PostgreSQL
    # (postgresql+asyncpg://...). Local dev may use sqlite+aiosqlite:///./data/renders.db.
    database_url: str = "sqlite+aiosqlite:///./data/renders.db"


settings = Settings()
