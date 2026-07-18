"""
Service layer for composition plan generation using ElevenLabs API.
"""

import logging
import os
import re
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from elevenlabs.client import ElevenLabs

from models.plan import (
    PlanGenerationRequest,
    CompositionPlanResponse,
    Chunk,
)


logger = logging.getLogger(__name__)

# Default music length in milliseconds (30 seconds)
DEFAULT_MUSIC_LENGTH_MS = 30000


def extract_duration_from_prompt(prompt: str) -> Optional[int]:
    """
    Extract duration in milliseconds from prompt text.
    
    Looks for patterns like:
    - "30-second", "30 second", "30 seconds"
    - "2-minute", "2 minute", "2 minutes"
    - "1.5 minute", "1.5 minutes"
    
    Args:
        prompt: The text prompt to parse.
        
    Returns:
        Duration in milliseconds if found, None otherwise.
    """
    # Pattern for seconds: "30-second", "30 second", "30 seconds", "30-seconds"
    seconds_pattern = r'(\d+(?:\.\d+)?)\s*[-\s]?\s*seconds?'
    
    # Pattern for minutes: "2-minute", "2 minute", "2 minutes", "1.5 minutes"
    minutes_pattern = r'(\d+(?:\.\d+)?)\s*[-\s]?\s*minutes?'
    
    # Try to find seconds first (more specific)
    seconds_match = re.search(seconds_pattern, prompt, re.IGNORECASE)
    if seconds_match:
        seconds = float(seconds_match.group(1))
        duration_ms = int(seconds * 1000)
        logger.info(f"Extracted duration from prompt: {seconds} seconds ({duration_ms}ms)")
        return duration_ms
    
    # Try to find minutes
    minutes_match = re.search(minutes_pattern, prompt, re.IGNORECASE)
    if minutes_match:
        minutes = float(minutes_match.group(1))
        duration_ms = int(minutes * 60 * 1000)
        logger.info(f"Extracted duration from prompt: {minutes} minutes ({duration_ms}ms)")
        return duration_ms
    
    return None


class PlanGeneratorService:
    """
    Service for generating composition plans using ElevenLabs API.
    
    This service uses the ElevenLabs music composition plan API to generate
    structured composition plans based on text prompts.
    """
    
    def __init__(self):
        """
        Initialize the plan generator service.
        """
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ELEVENLABS_API_KEY environment variable is not set. "
                "Please add it to your .env file or set it in your environment."
            )
        
        self._client = ElevenLabs(api_key=api_key)
        logger.info("Initialized PlanGeneratorService with ElevenLabs client")
    
    async def generate_plan(
        self,
        request: PlanGenerationRequest,
    ) -> CompositionPlanResponse:
        """
        Generate a composition plan based on the text prompt.
        
        Args:
            request: The validated plan generation request containing
                    the prompt and optionally music_length_ms.
        
        Returns:
            The generated composition plan.
        
        Raises:
            RuntimeError: If plan generation fails.
        """
        try:
            # Determine the music length to use:
            # 1. If explicitly provided, use that value
            # 2. Otherwise, try to extract from the prompt
            # 3. Fall back to default (30 seconds)
            if request.music_length_ms is not None:
                music_length_ms = request.music_length_ms
                logger.info(f"Using explicitly provided music_length_ms: {music_length_ms}ms")
            else:
                extracted_duration = extract_duration_from_prompt(request.prompt)
                if extracted_duration is not None:
                    # Clamp to valid range (1-300 seconds)
                    music_length_ms = max(1000, min(300000, extracted_duration))
                    if music_length_ms != extracted_duration:
                        logger.warning(
                            f"Extracted duration {extracted_duration}ms clamped to {music_length_ms}ms"
                        )
                else:
                    music_length_ms = DEFAULT_MUSIC_LENGTH_MS
                    logger.info(
                        f"No duration found in prompt, using default: {music_length_ms}ms"
                    )
            
            logger.info(
                f"Generating composition plan for prompt: '{request.prompt[:50]}...' "
                f"(length: {music_length_ms}ms)"
            )
            
            # Call the ElevenLabs API to create the composition plan
            composition_plan = self._client.music.composition_plan.create(
                prompt=request.prompt,
                music_length_ms=music_length_ms,
                model_id="music_v2",
            )
            
            # Convert the ElevenLabs response to our model
            plan_data = composition_plan.model_dump()
            
            # Build chunks from the response (music_v2 format)
            chunks = []
            for chunk_data in plan_data.get("chunks") or []:
                chunk = Chunk(
                    text=chunk_data.get("text", ""),
                    positive_styles=chunk_data.get("positive_styles", []),
                    negative_styles=chunk_data.get("negative_styles", []),
                    duration_ms=chunk_data.get("duration_ms", 0),
                    context_adherence=chunk_data.get("context_adherence"),
                )
                chunks.append(chunk)
            
            response = CompositionPlanResponse(chunks=chunks)
            
            logger.info(
                f"Successfully generated composition plan with {len(chunks)} chunks"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate composition plan: {e}", exc_info=True)
            raise RuntimeError(f"Composition plan generation failed: {str(e)}") from e


# Global service instance (initialized on first use)
_service_instance: Optional[PlanGeneratorService] = None


def get_plan_generator_service() -> PlanGeneratorService:
    """
    Get the singleton instance of the plan generator service.
    
    Returns:
        The PlanGeneratorService instance.
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = PlanGeneratorService()
    return _service_instance
