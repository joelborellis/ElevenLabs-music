"""
API routes for music rendering.
"""

import logging
import uuid
from datetime import datetime

from fastapi import (
    APIRouter,
    Request,
    status,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Depends,
)
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from opentelemetry import trace

from models.render import RenderRequest, RenderResponse
from models.websocket import ProgressMessage, ResultMessage, ErrorMessage, RenderWebSocketRequest
from services.render_service import get_render_service
from services.storage import get_storage_backend
from services import render_repository as repo
from db.database import get_db_session, get_sessionmaker


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/render", tags=["Music Render"])

# Get tracer for OpenTelemetry instrumentation
tracer = trace.get_tracer(__name__)


@router.post(
    "",
    response_model=RenderResponse,
    status_code=status.HTTP_200_OK,
    summary="Render music from composition plan",
    description="""
    Render music using the ElevenLabs API (compose_detailed).

    ## Input

    Provide EITHER a text prompt OR a composition plan (mutually exclusive):
    - **prompt**: A simple text description to generate a song from. May be
      combined with **music_length_ms** (3000-600000).
    - **chunks**: A music_v2 composition plan — an array of chunks (sections),
      each with positive_styles, negative_styles, duration_ms, text
      (lyrics/marker), and context_adherence.

    Additional pass-through parameters (all optional, with defaults):
    - **model_id** (default "music_v2"), **force_instrumental**,
      **store_for_inpainting**, **with_timestamps**, **sign_with_c2pa**,
      **output_format**
    - **finetune_id**: ID of an ElevenLabs finetune to steer generation
      (works in both prompt and plan modes). **finetune_strength** (0.0-1.0)
      optionally softens its influence.
    - **title**: local-only, used to name the saved output file (not sent to
      ElevenLabs).

    ## Response
    
    Returns metadata about the generated audio file including:
    - Filename and download URL
    - File size
    - Composition plan (with any modifications from the API)
    - Song metadata
    
    Use the download_url to stream or download the generated audio file.
    """,
    responses={
        200: {
            "description": "Successfully rendered music",
            "content": {
                "application/json": {
                    "example": {
                        "filename": "track_abc123.mp3",
                        "file_path": "/output/music/track_abc123.mp3",
                        "download_url": "/render/download/track_abc123.mp3",
                        "content_type": "audio/mpeg",
                        "file_size_bytes": 524288,
                        "request_id": "uuid-here",
                        "timestamp": "2024-01-01T00:00:00"
                    }
                }
            }
        },
        422: {"description": "Validation error - invalid composition plan"},
        500: {"description": "Internal server error during rendering"}
    }
)
async def render_music(
    request_data: RenderRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> RenderResponse:
    """
    Render music from a composition plan using the ElevenLabs API.

    Args:
        request_data: The composition plan to render
        request: The FastAPI request object (injected)
        session: Database session (injected)

    Returns:
        A response containing metadata about the generated audio file

    Raises:
        HTTPException: If rendering fails
    """
    request_id = getattr(request.state, "request_id", "unknown")

    with tracer.start_as_current_span("render_music") as span:
        span.set_attribute("request_id", request_id)
        span.set_attribute("chunks_count", len(request_data.chunks))

        try:
            mode = "prompt" if (request_data.prompt and request_data.prompt.strip()) else "plan"
            logger.info(
                f"Rendering music - request_id={request_id}, "
                f"mode={mode}, chunks={len(request_data.chunks)}"
            )

            # Get the render service and render the music (all compose_detailed
            # parameters are passed through from the validated request)
            render_service = get_render_service()
            result = render_service.render(request_data)

            # Persist the render metadata (audio bytes already in storage).
            # Best-effort: the render already succeeded and the file is already
            # in blob storage, so a DB hiccup (e.g. a transient connection
            # failure) must not turn a successful render into a 500.
            try:
                await repo.create_render(session, result, request_data, request_id)
            except Exception as e:
                logger.error(
                    f"Failed to persist render row (file is safe in storage) - "
                    f"request_id={request_id}, id={result.id}, error={str(e)}",
                    exc_info=True,
                )
                span.record_exception(e)

            span.set_attribute("render_id", result.id)
            span.set_attribute("filename", result.filename)
            span.set_attribute("file_size_bytes", result.file_size_bytes)

            logger.info(
                f"Render complete - request_id={request_id}, id={result.id}, "
                f"filename={result.filename}, size={result.file_size_bytes}"
            )

            return RenderResponse(
                id=result.id,
                filename=result.filename,
                file_path=result.blob_url,
                download_url=f"/render/download/{result.id}",
                stream_url=f"/render/stream/{result.id}",
                content_type=result.content_type,
                file_size_bytes=result.file_size_bytes,
                duration_ms=result.duration_ms,
                composition_plan=result.composition_plan,
                song_metadata=result.song_metadata,
                request_id=request_id,
                timestamp=datetime.utcnow().isoformat(),
            )

        except ValueError as e:
            # Validation errors should return 422
            logger.warning(
                f"Render validation failed - request_id={request_id}, error={str(e)}"
            )
            span.record_exception(e)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )
        except Exception as e:
            logger.error(
                f"Render failed - request_id={request_id}, error={str(e)}",
                exc_info=True
            )
            span.record_exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Music rendering failed: {str(e)}"
            )


async def _resolve_render(session: AsyncSession, identifier: str):
    """Resolve a render row by id, falling back to filename for backward compat.

    Returns the ORM row, or None if nothing matches.
    """
    row = await repo.get_by_id(session, identifier)
    if row is None:
        row = await repo.get_by_filename(session, identifier)
    return row


@router.get(
    "/download/{identifier}",
    summary="Download rendered audio file",
    description="Download a rendered audio file by render id (or filename for backward compat).",
    responses={
        200: {"description": "Audio file", "content": {"audio/mpeg": {}}},
        404: {"description": "File not found"},
    },
)
async def download_audio(
    identifier: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Download a rendered audio file by render id (or legacy filename)."""
    row = await _resolve_render(session, identifier)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Render not found: {identifier}",
        )

    storage = get_storage_backend()
    if not storage.exists(row.blob_key):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio object missing from storage: {row.blob_key}",
        )

    return StreamingResponse(
        storage.open_stream(row.blob_key),
        media_type=row.content_type,
        headers={
            "Content-Length": str(row.file_size_bytes),
            "Content-Disposition": f"attachment; filename={row.filename}",
            "Accept-Ranges": "bytes",
        },
    )


@router.get(
    "/stream/{identifier}",
    summary="Stream rendered audio file",
    description="Stream a rendered audio file for playback by render id (or filename).",
    responses={
        200: {"description": "Audio stream", "content": {"audio/mpeg": {}}},
        404: {"description": "File not found"},
    },
)
async def stream_audio(
    identifier: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Stream a rendered audio file for playback by render id (or legacy filename)."""
    row = await _resolve_render(session, identifier)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Render not found: {identifier}",
        )

    storage = get_storage_backend()
    if not storage.exists(row.blob_key):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio object missing from storage: {row.blob_key}",
        )

    return StreamingResponse(
        storage.open_stream(row.blob_key),
        media_type=row.content_type,
        headers={
            "Content-Length": str(row.file_size_bytes),
            "Accept-Ranges": "bytes",
            "Content-Disposition": f"inline; filename={row.filename}",
        },
    )


@router.websocket("/ws")
async def render_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for music rendering with real-time progress updates.

    Protocol:
    1. Client connects to /render/ws
    2. Server sends: {"type": "progress", "stage": "connected", "progress_percent": 0, ...}
    3. Client sends: {"type": "render", "composition_plan": {...}}
    4. Server sends progress updates as rendering proceeds
    5. Server sends final result: {"type": "result", "data": {...}}
    6. Connection closes

    Progress Stages:
    - connected (0%): WebSocket connection established
    - validating (5%): Validating composition plan
    - validated (10%): Validation complete
    - generating (15%): Starting ElevenLabs API call
    - processing (70%): API call complete, processing response
    - saving (85%): Saving audio file to disk
    - extracting (95%): Extracting metadata
    - complete (100%): All done

    Error Codes:
    - INVALID_REQUEST: Malformed request message
    - VALIDATION_ERROR: Composition plan validation failed
    - SERVER_ERROR: Unexpected error during rendering
    """
    await websocket.accept()
    request_id = str(uuid.uuid4())

    logger.info(f"WebSocket connection accepted - request_id={request_id}")

    # Send connected message
    await websocket.send_json(
        ProgressMessage(
            stage="connected",
            progress_percent=0,
            message="Connected. Send composition plan to begin rendering."
        ).model_dump()
    )

    try:
        # Wait for composition plan from client. A non-JSON payload here is a
        # genuinely malformed message -> INVALID_REQUEST.
        try:
            data = await websocket.receive_json()
        except Exception as e:
            logger.warning(f"Malformed WebSocket message - request_id={request_id}, error={str(e)}")
            await websocket.send_json(
                ErrorMessage(
                    error_code="INVALID_REQUEST",
                    message=f"Malformed message (expected JSON): {str(e)}"
                ).model_dump()
            )
            await websocket.close()
            return

        # Parse and validate the request. Distinguish a plan-content validation
        # failure (VALIDATION_ERROR) from a malformed message envelope
        # (INVALID_REQUEST) so the error code reflects what actually went wrong.
        try:
            ws_request = RenderWebSocketRequest(**data)
        except ValidationError as e:
            # If any error is located under composition_plan, the plan itself is
            # invalid; otherwise the message envelope (e.g. missing/incorrect
            # "type") is malformed.
            is_plan_error = any(
                err.get("loc") and err["loc"][0] == "composition_plan"
                for err in e.errors()
            )
            error_code = "VALIDATION_ERROR" if is_plan_error else "INVALID_REQUEST"
            logger.warning(
                f"Invalid WebSocket request - request_id={request_id}, "
                f"code={error_code}, error={str(e)}"
            )
            await websocket.send_json(
                ErrorMessage(
                    error_code=error_code,
                    message=str(e)
                ).model_dump()
            )
            await websocket.close()
            return
        except Exception as e:
            # e.g. data was not a dict -> cannot even build the request envelope
            logger.warning(f"Invalid WebSocket request - request_id={request_id}, error={str(e)}")
            await websocket.send_json(
                ErrorMessage(
                    error_code="INVALID_REQUEST",
                    message=f"Invalid request format: {str(e)}"
                ).model_dump()
            )
            await websocket.close()
            return

        # The wrapped composition_plan field is itself a full RenderRequest
        render_request = ws_request.composition_plan
        mode = "prompt" if (render_request.prompt and render_request.prompt.strip()) else "plan"

        logger.info(
            f"WebSocket render starting - request_id={request_id}, "
            f"mode={mode}, chunks={len(render_request.chunks)}"
        )

        # Define progress callback that sends WebSocket messages
        async def send_progress(stage: str, percent: int, message: str):
            await websocket.send_json(
                ProgressMessage(
                    stage=stage,
                    progress_percent=percent,
                    message=message
                ).model_dump()
            )

        # Get render service and execute with progress
        render_service = get_render_service()

        result = await render_service.render_with_progress(
            request=render_request,
            progress_callback=send_progress
        )

        # Persist the render metadata (WebSocket can't use Depends for a
        # per-message session, so open one explicitly). Best-effort: the
        # render already succeeded and the file is already in blob storage,
        # so a DB hiccup (e.g. a transient connection failure) must not
        # prevent the result from reaching the client.
        try:
            sessionmaker = get_sessionmaker()
            async with sessionmaker() as session:
                await repo.create_render(session, result, render_request, request_id)
        except Exception as e:
            logger.error(
                f"Failed to persist render row (file is safe in storage) - "
                f"request_id={request_id}, id={result.id}, error={str(e)}",
                exc_info=True,
            )

        # Build and send final response
        response = RenderResponse(
            id=result.id,
            filename=result.filename,
            file_path=result.blob_url,
            download_url=f"/render/download/{result.id}",
            stream_url=f"/render/stream/{result.id}",
            content_type=result.content_type,
            file_size_bytes=result.file_size_bytes,
            duration_ms=result.duration_ms,
            composition_plan=result.composition_plan,
            song_metadata=result.song_metadata,
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat(),
        )

        await websocket.send_json(
            ResultMessage(data=response.model_dump()).model_dump()
        )

        logger.info(
            f"WebSocket render complete - request_id={request_id}, "
            f"filename={result.filename}, size={result.file_size_bytes}"
        )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected by client - request_id={request_id}")
    except ValueError as e:
        # Validation errors
        logger.warning(f"WebSocket validation error - request_id={request_id}, error={str(e)}")
        try:
            await websocket.send_json(
                ErrorMessage(
                    error_code="VALIDATION_ERROR",
                    message=str(e)
                ).model_dump()
            )
        except Exception:
            pass  # Connection may already be closed
    except Exception as e:
        # Server errors
        logger.error(
            f"WebSocket error - request_id={request_id}, error={str(e)}",
            exc_info=True
        )
        try:
            await websocket.send_json(
                ErrorMessage(
                    error_code="SERVER_ERROR",
                    message=f"Music rendering failed: {str(e)}"
                ).model_dump()
            )
        except Exception:
            pass  # Connection may already be closed
    finally:
        try:
            await websocket.close()
        except Exception:
            pass  # Already closed
