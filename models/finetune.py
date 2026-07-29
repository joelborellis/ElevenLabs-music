"""
Response models for the finetunes listing endpoint.

These mirror the ElevenLabs ``GET /v1/music/finetunes`` payload so the frontend
can populate a finetune picker (id + name + genre/tags) without ever needing the
ElevenLabs API key.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FinetuneSummary(BaseModel):
    """A single ElevenLabs music finetune, as returned by the list endpoint."""

    # Ignore any additional fields the API may add in the future.
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Finetune id — pass this as 'finetune_id' to /render.")
    name: Optional[str] = Field(default=None, description="Human-readable finetune name.")
    tags: list[str] = Field(default_factory=list, description="Descriptive genre/style tags.")
    primary_genre: Optional[str] = Field(default=None, description="Primary genre label.")
    model_id: Optional[str] = Field(default=None, description="Generation model (e.g. 'music_v2').")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp.")
    visibility: Optional[str] = Field(default=None, description="'private', 'workspace', or 'public'.")
    created_by: Optional[str] = Field(default=None, description="Owner ('self', 'workspace', 'elevenlabs').")
    status: Optional[str] = Field(default=None, description="Training status (e.g. 'completed').")
    training_progress: Optional[float] = Field(default=None, description="Training progress 0.0-1.0.")
    failure_reason: Optional[str] = Field(default=None, description="Reason for failure, if any.")


class FinetuneContext(BaseModel):
    """The subset of a finetune's metadata handed to the prompt generator agent.

    Deliberately narrow: the agent derives genre, tempo, groove and instrumentation
    from these three fields, and nothing else about the finetune should reach it.
    """

    name: Optional[str] = Field(default=None, description="Human-readable finetune name.")
    primary_genre: Optional[str] = Field(default=None, description="Primary genre label.")
    tags: list[str] = Field(default_factory=list, description="Descriptive genre/style tags.")

    @classmethod
    def from_summary(cls, summary: "FinetuneSummary") -> "FinetuneContext":
        """Narrow a full FinetuneSummary down to the agent-facing fields."""
        return cls(
            name=summary.name,
            primary_genre=summary.primary_genre,
            tags=summary.tags,
        )


class FinetuneListResponse(BaseModel):
    """List of finetunes available to use with /render."""

    finetunes: list[FinetuneSummary] = Field(default_factory=list)
    count: int = Field(..., description="Number of finetunes returned in this page.")
    has_more: bool = Field(default=False, description="Whether more results exist beyond this page.")
    next_cursor: Optional[str] = Field(default=None, description="Cursor for the next page, if any.")
