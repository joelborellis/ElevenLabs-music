"""
WebSocket message models for render progress updates.
"""

from typing import Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from models.render import RenderRequest


class ProgressMessage(BaseModel):
    """Progress update sent from server to client during rendering."""

    type: Literal["progress"] = "progress"
    stage: str = Field(
        ...,
        description="Current processing stage (connected, validating, validated, generating, processing, saving, complete)"
    )
    progress_percent: int = Field(
        ...,
        ge=0,
        le=100,
        description="Progress percentage (0-100)"
    )
    message: str = Field(
        ...,
        description="Human-readable status message"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO 8601 timestamp"
    )


class ResultMessage(BaseModel):
    """Final result message sent from server to client after successful rendering."""

    type: Literal["result"] = "result"
    data: dict = Field(
        ...,
        description="RenderResponse data containing filename, URLs, metadata, etc."
    )


class ErrorMessage(BaseModel):
    """Error message sent from server to client when rendering fails."""

    type: Literal["error"] = "error"
    error_code: str = Field(
        ...,
        description="Machine-readable error code (VALIDATION_ERROR, SERVER_ERROR, INVALID_REQUEST)"
    )
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO 8601 timestamp"
    )


class RenderWebSocketRequest(BaseModel):
    """Request message from client to start rendering via WebSocket."""

    type: Literal["render"] = "render"
    composition_plan: RenderRequest = Field(
        ...,
        description="The composition plan to render (same structure as POST /render)"
    )
