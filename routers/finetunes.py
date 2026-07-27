"""
API routes for listing ElevenLabs music finetunes.

Lets the frontend fetch selectable finetunes (id + name + genre/tags) to pass as
``finetune_id`` on /render, without exposing the ElevenLabs API key client-side.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query, status, HTTPException
from opentelemetry import trace

from models.finetune import FinetuneListResponse
from services.finetune_service import get_finetune_service


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/finetunes", tags=["Finetunes"])

tracer = trace.get_tracer(__name__)


@router.get(
    "",
    response_model=FinetuneListResponse,
    status_code=status.HTTP_200_OK,
    summary="List available music finetunes",
    description="""
    List ElevenLabs music finetunes that can be used with /render.

    Each item includes the **id** (pass it as `finetune_id` on the /render
    request), plus name, tags, and primary_genre for building a picker.

    ## Query Parameters (all optional)
    - **model_id**: Keep only finetunes for this model (e.g. `music_v2`).
    - **visibility**: `private`, `workspace`, or `public`.
    - **created_by**: `self`, `workspace`, or `elevenlabs`.
    - **include_incomplete**: If true, also include finetunes still training
      (default false — only usable, completed finetunes are returned).
    - **cursor** / **page_size**: Pagination controls; use `next_cursor` from a
      previous response to fetch the next page.
    - **refresh**: Bypass the short-lived server cache and refetch from
      ElevenLabs.

    Results are cached in-memory for a few minutes (configurable via
    `FINETUNES_CACHE_TTL`) so repeated picker loads don't hit ElevenLabs each time.
    """,
    responses={
        200: {"description": "List of finetunes"},
        502: {"description": "Failed to reach ElevenLabs"},
    },
)
async def list_finetunes(
    model_id: Optional[str] = Query(default=None, description="Filter by model, e.g. 'music_v2'."),
    visibility: Optional[str] = Query(default=None, description="'private' | 'workspace' | 'public'."),
    created_by: Optional[str] = Query(default=None, description="'self' | 'workspace' | 'elevenlabs'."),
    include_incomplete: bool = Query(default=False, description="Include finetunes still training."),
    cursor: Optional[str] = Query(default=None, description="Pagination cursor (next_cursor)."),
    page_size: Optional[int] = Query(default=None, ge=1, le=100, description="Page size (1-100)."),
    refresh: bool = Query(default=False, description="Bypass the server cache and refetch."),
) -> FinetuneListResponse:
    """List music finetunes available for use with /render."""
    with tracer.start_as_current_span("list_finetunes") as span:
        try:
            service = get_finetune_service()
            result = service.list_finetunes(
                model_id=model_id,
                visibility=visibility,
                created_by=created_by,
                only_completed=not include_incomplete,
                cursor=cursor,
                page_size=page_size,
                force_refresh=refresh,
            )
            span.set_attribute("finetunes_count", result.count)
            return result
        except RuntimeError as e:
            # Missing API key / service misconfiguration
            logger.error(f"Finetune service unavailable: {e}")
            span.record_exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )
        except Exception as e:
            # Upstream (ElevenLabs) call failed
            logger.error(f"Failed to list finetunes: {e}", exc_info=True)
            span.record_exception(e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to list finetunes: {str(e)}",
            )
