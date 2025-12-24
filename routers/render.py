"""
API routes for music rendering.
"""

import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, status, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from opentelemetry import trace

from models.render import RenderRequest, RenderResponse
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
            composition_plan = request_data.model_dump()
            
            # Get the render service and render the music
            render_service = get_render_service()
            result = render_service.render(composition_plan)
            
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
