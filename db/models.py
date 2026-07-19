"""ORM models for persisted metadata."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, Text, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class Render(Base):
    """A single rendered music track and its metadata.

    The audio bytes themselves live in blob/object storage (``blob_key``); this
    row holds only metadata plus the storage reference.
    """

    __tablename__ = "renders"

    # Application-generated UUID (portable across SQLite/Postgres).
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Storage reference.
    blob_key: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    blob_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    filename: Mapped[str] = mapped_column(String(512), index=True)
    content_type: Mapped[str] = mapped_column(String(64), default="audio/mpeg")
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Generation inputs / provenance.
    model_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # "prompt" | "plan"
    output_format: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Structured metadata (JSON -> TEXT on SQLite, JSONB-capable on Postgres).
    composition_plan: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    song_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Tracking.
    request_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="complete")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
