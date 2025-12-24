"""
Service for rendering music using the ElevenLabs API.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


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
    
    def render(self, composition_plan: dict) -> RenderResult:
        """
        Render music from a composition plan using ElevenLabs API.
        
        Args:
            composition_plan: The composition plan dictionary
            
        Returns:
            RenderResult with file details and metadata
            
        Raises:
            Exception: If rendering fails
        """
        logger.info("Starting music render with ElevenLabs API")
        logger.debug(f"Composition plan sections: {len(composition_plan.get('sections', []))}")
        
        # Call ElevenLabs compose_detailed API
        track_details = self.client.music.compose_detailed(
            composition_plan=composition_plan,
        )
        
        logger.info(f"Render complete. Filename: {track_details.filename}")
        
        # Save the audio file
        output_path = self.output_dir / track_details.filename
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
            filename=track_details.filename,
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
