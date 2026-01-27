"""
Service for rendering music using the ElevenLabs API.
"""

import os
import re
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass

from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Type alias for progress callback function
ProgressCallback = Callable[[str, int, str], Awaitable[None]]


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
    filename: str
    file_path: str
    file_size_bytes: int
    composition_plan: Optional[dict] = None
    song_metadata: Optional[dict] = None


class RenderService:
    """Service for rendering music from composition plans."""
    
    def __init__(self):
        """Initialize the render service with ElevenLabs client."""
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ELEVENLABS_API_KEY environment variable is not set. "
                "Please add it to your .env file or set it in your environment."
            )
        
        self.client = ElevenLabs(api_key=api_key)
        
        # Create output directory for rendered music
        self.output_dir = Path(__file__).parent.parent / "output" / "music"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Render output directory: {self.output_dir}")
    
    def render(self, composition_plan: dict, title: str | None = None) -> RenderResult:
        """
        Render music from a composition plan using ElevenLabs API.

        Args:
            composition_plan: The composition plan dictionary
            title: Optional title to use for the output filename

        Returns:
            RenderResult with file details and metadata

        Raises:
            ValueError: If the composition plan is invalid
            Exception: If rendering fails
        """
        logger.info("Starting music render with ElevenLabs API")
        
        # Validate composition plan
        sections = composition_plan.get('sections', [])
        if not sections:
            raise ValueError(
                "Composition plan must have at least one section. "
                "Total duration must be between 3000ms and 600000ms."
            )
        
        total_duration_ms = sum(s.get('duration_ms', 0) for s in sections)
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
        
        # Validate individual section durations (each must be >= 3000ms)
        for i, section in enumerate(sections):
            section_duration = section.get('duration_ms', 0)
            if section_duration < 3000:
                raise ValueError(
                    f"Section '{section.get('section_name', i)}' duration ({section_duration}ms) "
                    "is too short. Each section must be at least 3000ms."
                )
        
        logger.debug(f"Composition plan sections: {len(sections)}, total duration: {total_duration_ms}ms")
        
        # Call ElevenLabs compose_detailed API
        track_details = self.client.music.compose_detailed(
            composition_plan=composition_plan,
        )
        
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

        # Determine output filename
        if title:
            output_filename = _sanitize_filename(title)
            logger.info(f"Using title-based filename: {output_filename}")
        else:
            output_filename = track_details.filename
            logger.info(f"Using ElevenLabs filename: {output_filename}")

        # Save the audio file
        output_path = self.output_dir / output_filename
        with open(output_path, "wb") as f:
            f.write(track_details.audio)
        
        file_size = output_path.stat().st_size
        logger.info(f"Saved audio to: {output_path} ({file_size} bytes)")
        
        # Extract metadata from the response
        json_data = track_details.json if hasattr(track_details, 'json') else None
        composition_plan_result = None
        song_metadata = None
        
        if json_data:
            composition_plan_result = json_data.get('composition_plan')
            song_metadata = json_data.get('song_metadata')
        
        return RenderResult(
            filename=output_filename,
            file_path=str(output_path),
            file_size_bytes=file_size,
            composition_plan=composition_plan_result,
            song_metadata=song_metadata,
        )

    async def render_with_progress(
        self,
        composition_plan: dict,
        title: str | None,
        progress_callback: ProgressCallback
    ) -> RenderResult:
        """
        Render music from a composition plan with progress callbacks for WebSocket updates.

        Args:
            composition_plan: The composition plan dictionary
            title: Optional title to use for the output filename
            progress_callback: Async callback function(stage, percent, message)

        Returns:
            RenderResult with file details and metadata

        Raises:
            ValueError: If the composition plan is invalid
            Exception: If rendering fails
        """
        logger.info("Starting music render with progress updates")

        # Stage 1: Validation
        await progress_callback("validating", 5, "Validating composition plan...")

        sections = composition_plan.get('sections', [])
        if not sections:
            raise ValueError(
                "Composition plan must have at least one section. "
                "Total duration must be between 3000ms and 600000ms."
            )

        total_duration_ms = sum(s.get('duration_ms', 0) for s in sections)
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

        for i, section in enumerate(sections):
            section_duration = section.get('duration_ms', 0)
            if section_duration < 3000:
                raise ValueError(
                    f"Section '{section.get('section_name', i)}' duration ({section_duration}ms) "
                    "is too short. Each section must be at least 3000ms."
                )

        await progress_callback("validated", 10, "Composition plan validated successfully")

        # Stage 2: API Call (the longest operation)
        await progress_callback("generating", 15, "Starting music generation with ElevenLabs API...")

        # Run blocking API call in thread pool to not block the event loop
        def blocking_api_call():
            return self.client.music.compose_detailed(composition_plan=composition_plan)

        # Create a task for the API call that runs in a thread pool
        api_task = asyncio.create_task(asyncio.to_thread(blocking_api_call))

        # Create a separate task to send simulated progress updates
        async def send_simulated_progress():
            simulated_progress = 20
            progress_messages = [
                "Analyzing composition structure...",
                "Generating musical elements...",
                "Synthesizing audio layers...",
                "Mixing tracks...",
                "Applying effects...",
                "Finalizing generation...",
            ]
            message_index = 0

            # Wait intervals: start fast, then slow down
            intervals = [1.0, 1.5, 2.0, 2.0, 2.5, 3.0, 3.0, 3.0]

            for interval in intervals:
                await asyncio.sleep(interval)

                # Stop if the API task is done
                if api_task.done():
                    break

                if simulated_progress <= 65:
                    message = progress_messages[message_index % len(progress_messages)]
                    logger.info(f"Sending simulated progress: {simulated_progress}% - {message}")
                    await progress_callback("generating", simulated_progress, message)
                    simulated_progress += 7
                    message_index += 1

        # Start the progress task
        progress_task = asyncio.create_task(send_simulated_progress())

        # Wait for the API task to complete
        try:
            track_details = await api_task
        finally:
            # Cancel the progress task if it's still running
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass

        logger.info("ElevenLabs API call completed")

        await progress_callback("processing", 70, "API call complete, processing response...")

        logger.info(f"Render complete. Filename: {track_details.filename}")

        # Stage 3: Determine filename
        if title:
            output_filename = _sanitize_filename(title)
            logger.info(f"Using title-based filename: {output_filename}")
        else:
            output_filename = track_details.filename
            logger.info(f"Using ElevenLabs filename: {output_filename}")

        # Stage 4: Save file
        await progress_callback("saving", 85, "Saving audio file to disk...")

        output_path = self.output_dir / output_filename
        with open(output_path, "wb") as f:
            f.write(track_details.audio)

        file_size = output_path.stat().st_size
        logger.info(f"Saved audio to: {output_path} ({file_size} bytes)")

        # Stage 5: Extract metadata
        await progress_callback("extracting", 95, "Extracting metadata...")

        json_data = track_details.json if hasattr(track_details, 'json') else None
        composition_plan_result = None
        song_metadata = None

        if json_data:
            composition_plan_result = json_data.get('composition_plan')
            song_metadata = json_data.get('song_metadata')

        await progress_callback("complete", 100, "Render complete!")

        return RenderResult(
            filename=output_filename,
            file_path=str(output_path),
            file_size_bytes=file_size,
            composition_plan=composition_plan_result,
            song_metadata=song_metadata,
        )

    def get_file_path(self, filename: str) -> Optional[Path]:
        """
        Get the full path to a rendered audio file.
        
        Args:
            filename: The filename of the audio file
            
        Returns:
            Path to the file if it exists, None otherwise
        """
        file_path = self.output_dir / filename
        if file_path.exists():
            return file_path
        return None


# Singleton instance
_render_service: Optional[RenderService] = None


def get_render_service() -> RenderService:
    """Get the singleton render service instance."""
    global _render_service
    if _render_service is None:
        _render_service = RenderService()
    return _render_service
