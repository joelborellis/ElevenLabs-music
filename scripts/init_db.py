"""
One-time database bootstrap.

Ensures the target database (from DATABASE_URL) exists on the PostgreSQL server,
then applies Alembic migrations to head. Safe to run repeatedly (idempotent).

For SQLite (local dev) the database file is created automatically by the driver,
so this script only runs the migrations.

Usage:
    uv run python scripts/init_db.py
"""

import asyncio
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings  # noqa: E402
from db.database import _normalize_db_url  # noqa: E402


async def ensure_postgres_database() -> None:
    """Create the target database if it does not already exist (Postgres only)."""
    url = settings.database_url
    if not url.startswith("postgresql"):
        print(f"[init_db] Non-Postgres URL ({url.split(':')[0]}) — skipping CREATE DATABASE.")
        return

    import asyncpg

    clean_url, connect_args = _normalize_db_url(url)
    parts = urlsplit(clean_url)
    target_db = parts.path.lstrip("/")
    if not target_db:
        raise RuntimeError("DATABASE_URL has no database name in its path.")

    # Connect to the maintenance 'postgres' database to issue CREATE DATABASE.
    admin_parts = parts._replace(path="/postgres")
    admin_url = urlunsplit(admin_parts).replace("postgresql+asyncpg", "postgresql")

    ssl_ctx = connect_args.get("ssl")
    print(f"[init_db] Connecting to maintenance DB to ensure '{target_db}' exists...")
    conn = await asyncpg.connect(admin_url, ssl=ssl_ctx)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", target_db
        )
        if exists:
            print(f"[init_db] Database '{target_db}' already exists.")
        else:
            # Identifier can't be parameterized; target_db comes from our own config.
            await conn.execute(f'CREATE DATABASE "{target_db}"')
            print(f"[init_db] Created database '{target_db}'.")
    finally:
        await conn.close()


def run_migrations() -> None:
    """Apply Alembic migrations to head using the current DATABASE_URL."""
    print("[init_db] Running 'alembic upgrade head'...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(Path(__file__).parent.parent),
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    print("[init_db] Migrations applied.")


def main() -> None:
    asyncio.run(ensure_postgres_database())
    run_migrations()
    print("[init_db] Done.")


if __name__ == "__main__":
    main()
