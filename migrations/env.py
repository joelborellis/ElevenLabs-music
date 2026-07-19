import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Make the project importable and pull in app config + models.
from config import settings
from db.database import Base, _normalize_db_url, _ensure_sqlite_dir
from db import models  # noqa: F401 - registers ORM tables on Base.metadata

# Ensure a local SQLite parent directory exists before connecting.
_ensure_sqlite_dir(settings.database_url)

# this is the Alembic Config object.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for 'autogenerate' support.
target_metadata = Base.metadata

# Resolve the runtime database URL (and SSL connect args) from app settings,
# not from alembic.ini, so migrations use the same DATABASE_URL as the app.
_DB_URL, _CONNECT_ARGS = _normalize_db_url(settings.database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (URL only, no DBAPI)."""
    context.configure(
        url=_DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations against it."""
    connectable = create_async_engine(
        _DB_URL,
        connect_args=_CONNECT_ARGS,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
