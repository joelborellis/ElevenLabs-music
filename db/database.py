"""
Async SQLAlchemy engine, session factory, and FastAPI wiring.

A single ``DATABASE_URL`` drives the connection:
- Production: ``postgresql+asyncpg://...`` (Azure Database for PostgreSQL).
- Local dev: ``sqlite+aiosqlite:///./data/renders.db``.

Azure Postgres requires TLS. asyncpg does not understand the libpq-style
``?ssl=require`` query parameter, so we strip it from the URL and pass a proper
SSL context via ``connect_args`` instead.
"""

import ssl
import logging
from pathlib import Path
from typing import AsyncGenerator, Optional
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


# Module-level engine + sessionmaker, initialized in init_db().
_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def _normalize_db_url(url: str) -> tuple[str, dict]:
    """Return (clean_url, connect_args).

    For asyncpg + Postgres, translate a ``ssl``/``sslmode`` query param into an
    SSL context connect arg (Azure Postgres requires TLS). SQLite is returned
    unchanged.
    """
    connect_args: dict = {}
    if not url.startswith("postgresql"):
        return url, connect_args

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    ssl_mode = query.pop("ssl", None) or query.pop("sslmode", None)

    if ssl_mode and ssl_mode.lower() not in ("disable", "false", "0"):
        # Standard verifying context; Azure Postgres presents a publicly-trusted cert.
        connect_args["ssl"] = ssl.create_default_context()

    clean_url = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
    return clean_url, connect_args


def _ensure_sqlite_dir(url: str) -> None:
    """Create the parent directory for a local SQLite database file if needed."""
    if not url.startswith("sqlite"):
        return
    # sqlite+aiosqlite:///./data/renders.db  ->  ./data/renders.db
    _, _, path = url.partition(":///")
    if path and path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)


def init_engine() -> AsyncEngine:
    """Create (once) and return the async engine."""
    global _engine, _sessionmaker
    if _engine is not None:
        return _engine

    _ensure_sqlite_dir(settings.database_url)
    clean_url, connect_args = _normalize_db_url(settings.database_url)

    _engine = create_async_engine(
        clean_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        echo=False,
    )
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    logger.info(f"Database engine initialized ({clean_url.split('@')[-1]})")
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the session factory, initializing the engine on first use."""
    if _sessionmaker is None:
        init_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def init_db(create_all: bool = False) -> None:
    """Initialize the engine on startup. Optionally create tables (dev convenience).

    In production, schema is managed by Alembic; ``create_all`` is intended only
    for local/dev or test databases.
    """
    init_engine()
    if create_all:
        from db import models  # noqa: F401 - ensure models are registered on Base

        assert _engine is not None
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ensured via create_all()")


async def dispose_db() -> None:
    """Dispose the engine on shutdown."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        logger.info("Database engine disposed")
    _engine = None
    _sessionmaker = None


async def check_db_health() -> dict:
    """Run a lightweight connectivity check (SELECT 1)."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "healthy"}


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a request-scoped async session."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session
