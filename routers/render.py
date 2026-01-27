"""
API routes for music rendering.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, status, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from opentelemetry import trace

from models.render import RenderRequest, RenderResponse
from models.websocket import ProgressMessage, ResultMessage, ErrorMessage, RenderWebSocketRequest
from services.render_service import get_render_service


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
    Render music from a composition plan using the ElevenLabs API.
    
    The composition plan includes global styles (positive and negative) and a list of
    sections with their own local styles, duration, and optional lyrics.
    
    ## Input
    
    A JSON composition plan with:
    - **positive_global_styles**: Style descriptors to include globally
    - **negative_global_styles**: Style descriptors to avoid globally
    - **sections**: Array of sections with local styles, duration, and lyrics
    
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
) -> RenderResponse:
    """
    Render music from a composition plan using the ElevenLabs API.
    
    Args:
        request_data: The composition plan to render
        request: The FastAPI request object (injected)
    
    Returns:
        A response containing metadata about the generated audio file
    
    Raises:
        HTTPException: If rendering fails
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    with tracer.start_as_current_span("render_music") as span:
        span.set_attribute("request_id", request_id)
        span.set_attribute("sections_count", len(request_data.sections))
        
        try:
            logger.info(
                f"Rendering music - request_id={request_id}, "
                f"sections={len(request_data.sections)}"
            )
            
            # Convert request to dict for the ElevenLabs API
            # Exclude title from composition_plan as it's only used for filename
            composition_plan = request_data.model_dump(exclude={"title"})

            # Get the render service and render the music
            render_service = get_render_service()
            result = render_service.render(composition_plan, title=request_data.title)
            
            span.set_attribute("filename", result.filename)
            span.set_attribute("file_size_bytes", result.file_size_bytes)
            
            logger.info(
                f"Render complete - request_id={request_id}, "
                f"filename={result.filename}, size={result.file_size_bytes}"
            )
            
            return RenderResponse(
                filename=result.filename,
                file_path=result.file_path,
                download_url=f"/render/download/{result.filename}",
                content_type="audio/mpeg",
                file_size_bytes=result.file_size_bytes,
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


@router.get(
    "/download/{filename}",
    summary="Download rendered audio file",
    description="Download a previously rendered audio file by filename.",
    responses={
        200: {
            "description": "Audio file",
            "content": {"audio/mpeg": {}}
        },
        404: {"description": "File not found"}
    }
)
async def download_audio(filename: str):
    """
    Download a rendered audio file.
    
    Args:
        filename: The filename of the audio to download
        
    Returns:
        The audio file as a streaming response
        
    Raises:
        HTTPException: If the file is not found
    """
    render_service = get_render_service()
    file_path = render_service.get_file_path(filename)
    
    if file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file not found: {filename}"
        )
    
    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=filename,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Accept-Ranges": "bytes",
        }
    )


@router.get(
    "/stream/{filename}",
    summary="Stream rendered audio file",
    description="Stream a previously rendered audio file for playback.",
    responses={
        200: {
            "description": "Audio stream",
            "content": {"audio/mpeg": {}}
        },
        404: {"description": "File not found"}
    }
)
async def stream_audio(filename: str):
    """
    Stream a rendered audio file for playback.
    
    Args:
        filename: The filename of the audio to stream
        
    Returns:
        The audio file as a streaming response suitable for playback
        
    Raises:
        HTTPException: If the file is not found
    """
    render_service = get_render_service()
    file_path = render_service.get_file_path(filename)
    
    if file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file not found: {filename}"
        )
    
    def iterfile():
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk
    
    file_size = file_path.stat().st_size
    
    return StreamingResponse(
        iterfile(),
        media_type="audio/mpeg",
        headers={
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Content-Disposition": f"inline; filename={filename}",
        }
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
        # Wait for composition plan from client
        data = await websocket.receive_json()

        # Parse and validate the request
        try:
            ws_request = RenderWebSocketRequest(**data)
        except Exception as e:
            logger.warning(f"Invalid WebSocket request - request_id={request_id}, error={str(e)}")
            await websocket.send_json(
                ErrorMessage(
                    error_code="INVALID_REQUEST",
                    message=f"Invalid request format: {str(e)}"
                ).model_dump()
            )
            await websocket.close()
            return

        # Extract composition plan data
        composition_plan = ws_request.composition_plan.model_dump(exclude={"title"})
        title = ws_request.composition_plan.title

        logger.info(
            f"WebSocket render starting - request_id={request_id}, "
            f"sections={len(composition_plan.get('sections', []))}"
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
            composition_plan=composition_plan,
            title=title,
            progress_callback=send_progress
        )

        # Build and send final response
        response = RenderResponse(
            filename=result.filename,
            file_path=result.file_path,
            download_url=f"/render/download/{result.filename}",
            stream_url=f"/render/stream/{result.filename}",
            content_type="audio/mpeg",
            file_size_bytes=result.file_size_bytes,
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
