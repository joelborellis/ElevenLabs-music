"""
Service for rendering music using the ElevenLabs API.
"""

import os
import re
import uuid
import asyncio
import logging
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass

from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

from models.render import RenderRequest
from services.storage import StorageBackend, get_storage_backend

load_dotenv()

logger = logging.getLogger(__name__)

# Type alias for progress callback function
ProgressCallback = Callable[[str, int, str], Awaitable[None]]


def _content_type_for(output_format: Optional[str]) -> str:
    """Best-effort MIME type for an ElevenLabs ``output_format`` (default mp3)."""
    if not output_format:
        return "audio/mpeg"
    fmt = output_format.lower()
    if fmt.startswith("mp3"):
        return "audio/mpeg"
    if fmt.startswith("pcm"):
        return "audio/pcm"
    if fmt.startswith("opus"):
        return "audio/opus"
    if fmt.startswith("wav"):
        return "audio/wav"
    return "audio/mpeg"


def _duration_ms_from(composition_plan: Optional[dict], request: RenderRequest) -> Optional[int]:
    """Derive total duration in ms from a composition plan or the request."""
    if composition_plan:
        chunks = composition_plan.get("chunks") or []
        total = sum(c.get("duration_ms", 0) for c in chunks)
        if total > 0:
            return total
    if request.chunks:
        total = sum(c.duration_ms for c in request.chunks if c.duration_ms)
        if total > 0:
            return total
    return request.music_length_ms


def _validate_composition_plan(composition_plan: dict) -> tuple[list, int]:
    """
    Validate a composition plan and return chunks and total duration.

    Args:
        composition_plan: The composition plan dictionary (music_v2 format)

    Returns:
        Tuple of (chunks list, total_duration_ms)

    Raises:
        ValueError: If the composition plan is invalid
    """
    chunks = composition_plan.get('chunks', [])
    if not chunks:
        raise ValueError(
            "Composition plan must have at least one chunk. "
            "Total duration must be between 3000ms and 600000ms."
        )

    total_duration_ms = sum(c.get('duration_ms', 0) for c in chunks)
    if total_duration_ms < 3000:
        raise ValueError(
            f"Composition plan total duration ({total_duration_ms}ms) is too short. "
            "Minimum duration is 3000ms."
        )
    if total_duration_ms > 600000:
        raise ValueError(
            f"Composition plan total duration ({total_duration_ms}ms) is too long. "
            "Maximum duration is 600000ms (10 minutes)."
        )

    for i, chunk in enumerate(chunks):
        chunk_duration = chunk.get('duration_ms', 0)
        if chunk_duration < 3000:
            raise ValueError(
                f"Chunk '{chunk.get('text', i)}' duration ({chunk_duration}ms) "
                "is too short. Each chunk must be at least 3000ms."
            )

    return chunks, total_duration_ms


def _sanitize_filename(title: str) -> str:
    """Convert title to a safe filename."""
    # Convert to lowercase, replace spaces with underscores
    sanitized = title.lower().strip()
    sanitized = re.sub(r'\s+', '_', sanitized)
    # Remove any characters that aren't alphanumeric, underscore, or hyphen
    sanitized = re.sub(r'[^\w\-]', '', sanitized)
    # Truncate to reasonable length (max 50 chars)
    sanitized = sanitized[:50]
    # Add short unique suffix to prevent collisions
    unique_suffix = uuid.uuid4().hex[:8]
    return f"{sanitized}_{unique_suffix}.mp3"


@dataclass
class RenderResult:
    """Result of a music render operation."""
    id: str
    filename: str
    blob_key: str
    content_type: str
    file_size_bytes: int
    blob_url: Optional[str] = None
    duration_ms: Optional[int] = None
    composition_plan: Optional[dict] = None
    song_metadata: Optional[dict] = None


class RenderService:
    """Service for rendering music from composition plans."""

    def __init__(self, storage: Optional[StorageBackend] = None):
        """Initialize the render service with ElevenLabs client and storage backend."""
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ELEVENLABS_API_KEY environment variable is not set. "
                "Please add it to your .env file or set it in your environment."
            )

        self.client = ElevenLabs(api_key=api_key)

        # Storage backend for rendered audio (local filesystem or Azure Blob).
        self.storage = storage or get_storage_backend()

    def _compose(self, compose_kwargs: dict):
        """Invoke ``compose_detailed``, routing around the SDK wrapper for finetunes.

        The installed SDK's custom ``MusicClient.compose_detailed`` wrapper only
        forwards a fixed subset of parameters; ``finetune_id`` and
        ``finetune_strength`` fall into its ``**kwargs`` and are silently dropped
        (never sent to the API). When either is requested we call the raw
        autogenerated client directly and reuse the wrapper's multipart parser,
        so the returned object is identical to the normal path.
        """
        music = self.client.music

        if "finetune_id" not in compose_kwargs and "finetune_strength" not in compose_kwargs:
            return music.compose_detailed(**compose_kwargs)

        # The raw client uses ``sign_with_c_2_pa``; the wrapper exposes it as
        # ``sign_with_c2pa``. Translate before hitting the raw client.
        raw_kwargs = dict(compose_kwargs)
        if "sign_with_c2pa" in raw_kwargs:
            raw_kwargs["sign_with_c_2_pa"] = raw_kwargs.pop("sign_with_c2pa")

        logger.info(
            "Using raw compose_detailed path for finetune "
            f"(finetune_id={compose_kwargs.get('finetune_id')}, "
            f"finetune_strength={compose_kwargs.get('finetune_strength')})"
        )
        with music._raw_client.compose_detailed(**raw_kwargs) as r:
            result = music._parse_multipart(r.data)
            result.song_id = r.headers.get("song-id")
            return result
    
    def render(self, request: RenderRequest) -> RenderResult:
        """
        Render music from a render request using the ElevenLabs API.

        Passes through all supported ``compose_detailed`` parameters (prompt or
        composition plan, model, instrumental flag, output format, etc.).

        Args:
            request: The validated render request

        Returns:
            RenderResult with file details and metadata

        Raises:
            ValueError: If the composition plan is invalid
            Exception: If rendering fails
        """
        logger.info("Starting music render with ElevenLabs API")

        compose_kwargs = request.to_compose_kwargs()

        # Validate the composition plan only in plan-mode (prompt-mode has none)
        if "composition_plan" in compose_kwargs:
            chunks, total_duration_ms = _validate_composition_plan(compose_kwargs["composition_plan"])
            logger.debug(f"Composition plan chunks: {len(chunks)}, total duration: {total_duration_ms}ms")
        else:
            logger.debug(f"Prompt-mode render (music_length_ms={request.music_length_ms})")

        # Call ElevenLabs compose_detailed API with all requested parameters
        track_details = self._compose(compose_kwargs)

        logger.info(f"Render complete. Filename: {track_details.filename}")
        
        # Log all available attributes on track_details for debugging
        logger.info("=" * 60)
        logger.info("TRACK_DETAILS RESPONSE ATTRIBUTES:")
        logger.info("=" * 60)
        for attr in dir(track_details):
            if not attr.startswith('_'):
                try:
                    value = getattr(track_details, attr)
                    if not callable(value):
                        # Don't log the full audio bytes
                        if attr == 'audio':
                            logger.info(f"  {attr}: <bytes, length={len(value)}>")
                        else:
                            logger.info(f"  {attr}: {value}")
                except Exception as e:
                    logger.info(f"  {attr}: <error accessing: {e}>")
        logger.info("=" * 60)

        # Determine output filename (used as the storage key)
        if request.title:
            output_filename = _sanitize_filename(request.title)
            logger.info(f"Using title-based filename: {output_filename}")
        else:
            output_filename = track_details.filename
            logger.info(f"Using ElevenLabs filename: {output_filename}")

        # Save the audio via the storage backend (local filesystem or Azure Blob)
        content_type = _content_type_for(request.output_format)
        audio_bytes = track_details.audio
        file_size = len(audio_bytes)
        blob_url = self.storage.save(output_filename, audio_bytes, content_type)
        logger.info(f"Saved audio to storage key '{output_filename}' ({file_size} bytes)")

        # Extract metadata from the response
        json_data = track_details.json if hasattr(track_details, 'json') else None
        composition_plan_result = None
        song_metadata = None

        if json_data:
            composition_plan_result = json_data.get('composition_plan')
            song_metadata = json_data.get('song_metadata')

        return RenderResult(
            id=str(uuid.uuid4()),
            filename=output_filename,
            blob_key=output_filename,
            content_type=content_type,
            file_size_bytes=file_size,
            blob_url=blob_url,
            duration_ms=_duration_ms_from(composition_plan_result, request),
            composition_plan=composition_plan_result,
            song_metadata=song_metadata,
        )

    async def render_with_progress(
        self,
        request: RenderRequest,
        progress_callback: ProgressCallback
    ) -> RenderResult:
        """
        Render music from a render request with progress callbacks for WebSocket updates.

        Passes through all supported ``compose_detailed`` parameters (prompt or
        composition plan, model, instrumental flag, output format, etc.).

        Args:
            request: The validated render request
            progress_callback: Async callback function(stage, percent, message)

        Returns:
            RenderResult with file details and metadata

        Raises:
            ValueError: If the composition plan is invalid
            Exception: If rendering fails
        """
        logger.info("Starting music render with progress updates")

        compose_kwargs = request.to_compose_kwargs()

        # Stage 1: Validation (composition plan only; prompt-mode has no plan)
        await progress_callback("validating", 5, "Validating render request...")
        if "composition_plan" in compose_kwargs:
            _validate_composition_plan(compose_kwargs["composition_plan"])
            await progress_callback("validated", 10, "Composition plan validated")
        else:
            await progress_callback("validated", 10, "Prompt accepted")

        # Stage 2: API Call with simulated progress
        await progress_callback("generating", 15, "Generating music with ElevenLabs API...")

        # Run API call in thread pool as a task
        api_task = asyncio.create_task(
            asyncio.to_thread(self._compose, compose_kwargs)
        )

        # Simulated progress: increment every 2 seconds until API completes
        current_progress = 20
        while not api_task.done():
            await asyncio.sleep(2.0)
            if not api_task.done() and current_progress < 65:
                current_progress += 5
                await progress_callback(
                    "generating",
                    current_progress,
                    "Generating music..."
                )

        track_details = await api_task
        logger.info("ElevenLabs API call completed")
        logger.info(f"Render complete. Filename: {track_details.filename}")

        # Continue gradual progress through post-processing stages
        # Use shorter intervals since actual work is fast
        async def increment_to(target: int, stage: str, message: str):
            nonlocal current_progress
            while current_progress < target:
                current_progress += 5
                await progress_callback(stage, current_progress, message)
                await asyncio.sleep(0.5)

        # Stage 3: Processing response (progress to 75%)
        await increment_to(75, "processing", "Processing response...")

        # Stage 4: Determine filename (used as the storage key)
        if request.title:
            output_filename = _sanitize_filename(request.title)
            logger.info(f"Using title-based filename: {output_filename}")
        else:
            output_filename = track_details.filename
            logger.info(f"Using ElevenLabs filename: {output_filename}")

        # Stage 5: Save file (progress to 90%) — uploading to storage backend.
        # The Azure SDK client is synchronous, so run it in a thread to avoid
        # blocking the event loop (same pattern as the compose_detailed call).
        await increment_to(90, "saving", "Saving audio file...")

        content_type = _content_type_for(request.output_format)
        audio_bytes = track_details.audio
        file_size = len(audio_bytes)
        blob_url = await asyncio.to_thread(
            self.storage.save, output_filename, audio_bytes, content_type
        )
        logger.info(f"Saved audio to storage key '{output_filename}' ({file_size} bytes)")

        # Stage 6: Extract metadata (progress to 95%)
        await increment_to(95, "extracting", "Extracting metadata...")

        json_data = track_details.json if hasattr(track_details, 'json') else None
        composition_plan_result = None
        song_metadata = None

        if json_data:
            composition_plan_result = json_data.get('composition_plan')
            song_metadata = json_data.get('song_metadata')

        # Final progress to 100%
        await progress_callback("complete", 100, "Render complete!")

        return RenderResult(
            id=str(uuid.uuid4()),
            filename=output_filename,
            blob_key=output_filename,
            content_type=content_type,
            file_size_bytes=file_size,
            blob_url=blob_url,
            duration_ms=_duration_ms_from(composition_plan_result, request),
            composition_plan=composition_plan_result,
            song_metadata=song_metadata,
        )

    def resolve_key(self, filename: str) -> Optional[str]:
        """Return the storage key for ``filename`` if it exists, else None.

        The storage key is the filename itself (see ``render``). This replaces the
        old filesystem-path lookup so it works uniformly for local and Azure.
        """
        return filename if self.storage.exists(filename) else None


# Singleton instance
_render_service: Optional[RenderService] = None


def get_render_service() -> RenderService:
    """Get the singleton render service instance."""
    global _render_service
    if _render_service is None:
        _render_service = RenderService()
    return _render_service
