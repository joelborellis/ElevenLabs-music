"""
Service layer for composition plan generation using ElevenLabs API.
"""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from elevenlabs.client import ElevenLabs

from models.plan import (
    PlanGenerationRequest,
    CompositionPlanResponse,
    Section,
)


logger = logging.getLogger(__name__)


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
                    the prompt and music_length_ms.
        
        Returns:
            The generated composition plan.
        
        Raises:
            RuntimeError: If plan generation fails.
        """
        try:
            logger.info(
                f"Generating composition plan for prompt: '{request.prompt[:50]}...' "
                f"(length: {request.music_length_ms}ms)"
            )
            
            # Call the ElevenLabs API to create the composition plan
            composition_plan = self._client.music.composition_plan.create(
                prompt=request.prompt,
                music_length_ms=request.music_length_ms,
            )
            
            # Convert the ElevenLabs response to our model
            plan_data = composition_plan.model_dump()
            
            # Build sections from the response
            sections = []
            for section_data in plan_data.get("sections", []):
                section = Section(
                    section_name=section_data.get("section_name", ""),
                    positive_local_styles=section_data.get("positive_local_styles", []),
                    negative_local_styles=section_data.get("negative_local_styles", []),
                    duration_ms=section_data.get("duration_ms", 0),
                    lines=section_data.get("lines", []),
                    source_from=section_data.get("source_from"),
                )
                sections.append(section)
            
            response = CompositionPlanResponse(
                positive_global_styles=plan_data.get("positive_global_styles", []),
                negative_global_styles=plan_data.get("negative_global_styles", []),
                sections=sections,
            )
            
            logger.info(
                f"Successfully generated composition plan with {len(sections)} sections"
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
