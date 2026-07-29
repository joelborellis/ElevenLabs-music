"""
Service for listing ElevenLabs music finetunes.

Proxies the ElevenLabs ``music.finetunes.list`` call so the frontend can fetch
selectable finetunes through this backend (keeping the API key server-side).
"""

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

from models.finetune import FinetuneSummary, FinetuneListResponse

load_dotenv()

logger = logging.getLogger(__name__)

# How long a fetched finetunes page stays fresh, in seconds. Finetunes change
# rarely, so a short TTL avoids hitting ElevenLabs on every picker load.
# Override with FINETUNES_CACHE_TTL; set to 0 to disable caching.
CACHE_TTL_SECONDS = float(os.getenv("FINETUNES_CACHE_TTL", "300"))


@dataclass
class _CacheEntry:
    """A cached upstream fetch (pre-filter) with its wall-clock fetch time."""
    fetched_at: float
    summaries: list[FinetuneSummary]
    has_more: bool
    next_cursor: Optional[str]


@dataclass
class _IdCacheEntry:
    """A cached single-finetune lookup. ``summary`` is None for a known miss."""
    fetched_at: float
    summary: Optional[FinetuneSummary]


class FinetuneService:
    """Service for retrieving available music finetunes from ElevenLabs."""

    def __init__(self):
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ELEVENLABS_API_KEY environment variable is not set. "
                "Please add it to your .env file or set it in your environment."
            )
        self._client = ElevenLabs(api_key=api_key)

        # TTL cache keyed on the upstream call params only. Client-side filters
        # (model_id, only_completed) are applied per-request to the cached data,
        # so one fetch can serve many filter combinations.
        self._cache: dict[tuple, _CacheEntry] = {}
        # Single-id lookups that missed the page cache, keyed on finetune id.
        self._id_cache: dict[str, _IdCacheEntry] = {}
        self._cache_lock = threading.Lock()

    def _fetch_page(
        self,
        *,
        visibility: Optional[str],
        created_by: Optional[str],
        cursor: Optional[str],
        page_size: Optional[int],
        force_refresh: bool,
    ) -> _CacheEntry:
        """Return a cache entry for these upstream params, fetching if stale."""
        key = (visibility, created_by, cursor, page_size)
        now = time.monotonic()

        if not force_refresh and CACHE_TTL_SECONDS > 0:
            with self._cache_lock:
                entry = self._cache.get(key)
                if entry is not None and (now - entry.fetched_at) < CACHE_TTL_SECONDS:
                    logger.debug("Finetunes cache hit for key=%s", key)
                    return entry

        res = self._client.music.finetunes.list(
            visibility=visibility,
            created_by=created_by,
            cursor=cursor,
            page_size=page_size,
        )
        raw_items = res.finetunes or []
        summaries = [
            FinetuneSummary.model_validate(ft.dict() if hasattr(ft, "dict") else ft)
            for ft in raw_items
        ]
        entry = _CacheEntry(
            fetched_at=time.monotonic(),
            summaries=summaries,
            has_more=bool(getattr(res, "has_more", False)),
            next_cursor=getattr(res, "next_cursor", None),
        )
        logger.info("Fetched %d finetunes from ElevenLabs (key=%s)", len(summaries), key)

        if CACHE_TTL_SECONDS > 0:
            with self._cache_lock:
                self._cache[key] = entry
        return entry

    def clear_cache(self) -> None:
        """Drop all cached finetune pages and id lookups (next call refetches)."""
        with self._cache_lock:
            self._cache.clear()
            self._id_cache.clear()

    def get_finetune(self, finetune_id: str) -> Optional[FinetuneSummary]:
        """Look up a single finetune by id.

        Checks the cached list pages first — a picker load usually warmed them, so
        the common path costs nothing and adds no latency to /prompt. Falls back to
        the upstream single-finetune endpoint for ids that aren't on a cached page.

        Never raises: a deleted finetune or an unreachable ElevenLabs must degrade
        the prompt (callers infer genre from the slug alone), not fail the request.

        Args:
            finetune_id: The finetune id to resolve.

        Returns:
            The matching FinetuneSummary, or None if it is unknown or unreachable.
        """
        if not finetune_id:
            return None

        now = time.monotonic()

        with self._cache_lock:
            # Page cache holds pre-filter summaries, so this hits regardless of the
            # only_completed / model_id filters any earlier listing applied.
            for entry in self._cache.values():
                if CACHE_TTL_SECONDS > 0 and (now - entry.fetched_at) >= CACHE_TTL_SECONDS:
                    continue
                for summary in entry.summaries:
                    if summary.id == finetune_id:
                        logger.debug("Finetune %s resolved from page cache", finetune_id)
                        return summary

            id_entry = self._id_cache.get(finetune_id)
            if (
                id_entry is not None
                and CACHE_TTL_SECONDS > 0
                and (now - id_entry.fetched_at) < CACHE_TTL_SECONDS
            ):
                logger.debug("Finetune %s resolved from id cache", finetune_id)
                return id_entry.summary

        try:
            ft = self._client.music.finetunes.get(finetune_id)
            summary = FinetuneSummary.model_validate(
                ft.dict() if hasattr(ft, "dict") else ft
            )
            logger.info(
                "Fetched finetune %s from ElevenLabs (name=%r, primary_genre=%r)",
                finetune_id, summary.name, summary.primary_genre,
            )
        except Exception as e:
            # Deleted finetune, bad id, or ElevenLabs unreachable. Cache the miss so
            # a burst of requests for a dead id doesn't hammer the upstream.
            logger.warning("Could not resolve finetune %s: %s", finetune_id, e)
            summary = None

        if CACHE_TTL_SECONDS > 0:
            with self._cache_lock:
                self._id_cache[finetune_id] = _IdCacheEntry(
                    fetched_at=time.monotonic(),
                    summary=summary,
                )
        return summary

    def list_finetunes(
        self,
        *,
        model_id: Optional[str] = None,
        visibility: Optional[str] = None,
        created_by: Optional[str] = None,
        only_completed: bool = True,
        cursor: Optional[str] = None,
        page_size: Optional[int] = None,
        force_refresh: bool = False,
    ) -> FinetuneListResponse:
        """List finetunes, optionally filtered to those usable for rendering.

        Results from ElevenLabs are cached for ``CACHE_TTL_SECONDS`` (keyed on the
        upstream call params); the ``model_id`` / ``only_completed`` filters are
        applied to the cached data per request.

        Args:
            model_id: Keep only finetunes for this model (e.g. 'music_v2').
            visibility: Pass through to the API ('private'|'workspace'|'public').
            created_by: Pass through to the API ('self'|'workspace'|'elevenlabs').
            only_completed: Drop finetunes that are not finished training
                (the default) so the picker only shows usable ones.
            cursor: Pagination cursor from a previous response's next_cursor.
            page_size: Page size to request from the API.
            force_refresh: Bypass the cache and refetch from ElevenLabs.

        Returns:
            A FinetuneListResponse with the (filtered) finetunes.
        """
        entry = self._fetch_page(
            visibility=visibility,
            created_by=created_by,
            cursor=cursor,
            page_size=page_size,
            force_refresh=force_refresh,
        )

        summaries = entry.summaries
        if only_completed:
            summaries = [s for s in summaries if s.status == "completed"]
        if model_id:
            summaries = [s for s in summaries if s.model_id == model_id]

        logger.info(
            "Listed finetunes: %d returned (raw=%d, only_completed=%s, model_id=%s)",
            len(summaries), len(entry.summaries), only_completed, model_id,
        )

        return FinetuneListResponse(
            finetunes=summaries,
            count=len(summaries),
            has_more=entry.has_more,
            next_cursor=entry.next_cursor,
        )


# Singleton instance
_finetune_service: Optional[FinetuneService] = None


def get_finetune_service() -> FinetuneService:
    """Get the singleton finetune service instance."""
    global _finetune_service
    if _finetune_service is None:
        _finetune_service = FinetuneService()
    return _finetune_service
