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


def _validate_composition_plan(composition_plan: dict) -> tuple[list, int]:
    """
    Validate a composition plan and return sections and total duration.

    Args:
        composition_plan: The composition plan dictionary

    Returns:
        Tuple of (sections list, total_duration_ms)

    Raises:
        ValueError: If the composition plan is invalid
    """
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

    return sections, total_duration_ms


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
        sections, total_duration_ms = _validate_composition_plan(composition_plan)
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
        sections, total_duration_ms = _validate_composition_plan(composition_plan)
        await progress_callback("validated", 10, "Composition plan validated")

        # Stage 2: API Call with simulated progress
        await progress_callback("generating", 15, "Generating music with ElevenLabs API...")

        # Run API call in thread pool as a task
        api_task = asyncio.create_task(
            asyncio.to_thread(
                self.client.music.compose_detailed,
                composition_plan=composition_plan
            )
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

        # Stage 4: Determine filename
        if title:
            output_filename = _sanitize_filename(title)
            logger.info(f"Using title-based filename: {output_filename}")
        else:
            output_filename = track_details.filename
            logger.info(f"Using ElevenLabs filename: {output_filename}")

        # Stage 5: Save file (progress to 90%)
        await increment_to(90, "saving", "Saving audio file...")

        output_path = self.output_dir / output_filename
        with open(output_path, "wb") as f:
            f.write(track_details.audio)

        file_size = output_path.stat().st_size
        logger.info(f"Saved audio to: {output_path} ({file_size} bytes)")

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
