# syntax=docker/dockerfile:1
FROM python:3.12-alpine

# uv for fast, reproducible installs (copied from the official uv image).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Reproducible, non-editable installs; keep the venv inside the image.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Install dependencies first (better layer caching). --no-dev excludes aiosqlite;
# production uses asyncpg against Azure Database for PostgreSQL.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy the application source and finish the install.
COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000

# Migrations are NOT run here (avoids per-replica concurrent alembic upgrades);
# schema is applied out-of-band. See docs/DEPLOYMENT.md.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
