"""
Data-access layer for the ``renders`` table.

Keeps all SQL/ORM access in one place so routers and services never build queries
directly.
"""

import logging
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Render
from models.render import RenderRequest
from services.render_service import RenderResult

logger = logging.getLogger(__name__)


async def create_render(
    session: AsyncSession,
    result: RenderResult,
    request: RenderRequest,
    request_id: Optional[str] = None,
) -> Render:
    """Persist a completed render and return the ORM row."""
    mode = "prompt" if (request.prompt and request.prompt.strip()) else "plan"
    row = Render(
        id=result.id,
        blob_key=result.blob_key,
        blob_url=result.blob_url,
        filename=result.filename,
        content_type=result.content_type,
        file_size_bytes=result.file_size_bytes,
        duration_ms=result.duration_ms,
        model_id=request.model_id,
        title=request.title,
        prompt=request.prompt,
        mode=mode,
        output_format=request.output_format,
        composition_plan=result.composition_plan,
        song_metadata=result.song_metadata,
        request_id=request_id,
        status="complete",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    logger.info(f"Persisted render row id={row.id} key={row.blob_key}")
    return row


async def get_by_id(session: AsyncSession, render_id: str) -> Optional[Render]:
    """Look up a render by its id."""
    return await session.get(Render, render_id)


async def get_by_filename(session: AsyncSession, filename: str) -> Optional[Render]:
    """Look up the most recent render matching a filename (backward-compat path)."""
    stmt = (
        select(Render)
        .where(Render.filename == filename)
        .order_by(Render.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_renders(
    session: AsyncSession, limit: int = 50, offset: int = 0
) -> Sequence[Render]:
    """List renders, newest first."""
    stmt = (
        select(Render)
        .order_by(Render.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return (await session.execute(stmt)).scalars().all()
