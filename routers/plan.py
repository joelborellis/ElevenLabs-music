"""
API routes for composition plan generation.
"""

import logging

from fastapi import APIRouter, Request, status, HTTPException
from opentelemetry import trace

from models.plan import (
    PlanGenerationRequest,
    CompositionPlanResponse,
)
from services.plan_generator import get_plan_generator_service


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/plan", tags=["Composition Plan"])

# Get tracer for OpenTelemetry instrumentation
tracer = trace.get_tracer(__name__)


@router.post(
    "",
    response_model=CompositionPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate composition plan",
    description="""
    Generate a composition plan using the ElevenLabs music API based on a text prompt.
    
    The composition plan includes global styles (positive and negative) and a list of
    sections with their own local styles, duration, and optional lyrics.
    
    ## Input Parameters
    
    - **prompt**: A text description of the desired music composition
    - **music_length_ms**: Total length of the music in milliseconds (default: 30000)
    
    ## Example Request
    
    ```json
    {
      "prompt": "Create an uplifting electronic pop track with a catchy hook",
      "music_length_ms": 30000
    }
    ```
    
    ## Response
    
    Returns a structured composition plan with:
    - Global positive and negative styles
    - Sections with local styles, duration, and optional lyrics
    """,
    responses={
        200: {
            "description": "Successfully generated composition plan",
            "content": {
                "application/json": {
                    "example": {
                        "positive_global_styles": ["electronic pop", "uplifting"],
                        "negative_global_styles": ["dark", "slow tempo"],
                        "sections": [
                            {
                                "section_name": "Intro",
                                "positive_local_styles": ["bright synths"],
                                "negative_local_styles": ["vocals"],
                                "duration_ms": 3000,
                                "lines": [],
                                "source_from": None
                            }
                        ]
                    }
                }
            }
        },
        422: {"description": "Validation error - invalid input parameters"},
        500: {"description": "Internal server error during plan generation"}
    }
)
async def generate_plan(
    request_data: PlanGenerationRequest,
    request: Request,
) -> CompositionPlanResponse:
    """
    Generate a composition plan using the ElevenLabs API.
    
    This endpoint takes a text prompt and generates a structured composition plan
    that can be used for music generation with the ElevenLabs music API.
    
    Args:
        request_data: The plan generation request with prompt and length
        request: The FastAPI request object (injected)
    
    Returns:
        A response containing the generated composition plan and metadata
    
    Raises:
        HTTPException: If plan generation fails
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    with tracer.start_as_current_span("generate_composition_plan") as span:
        # Add trace attributes
        span.set_attribute("plan.prompt_length", len(request_data.prompt))
        span.set_attribute("plan.music_length_ms", request_data.music_length_ms)
        span.set_attribute("request.id", request_id)
        
        try:
            # Log the request for debugging
            logger.info(
                f"Received plan generation request",
                extra={
                    "request_id": request_id,
                    "prompt_preview": request_data.prompt[:100] + "..." if len(request_data.prompt) > 100 else request_data.prompt,
                    "music_length_ms": request_data.music_length_ms,
                }
            )
            
            # Get the service instance
            service = get_plan_generator_service()
            
            # Generate the composition plan using the ElevenLabs API
            with tracer.start_as_current_span("elevenlabs_api_call"):
                generated_plan = await service.generate_plan(request_data)
            
            span.set_attribute("plan.sections_count", len(generated_plan.sections))
            span.set_attribute("success", True)
            
            logger.info(
                f"Successfully generated composition plan",
                extra={
                    "request_id": request_id,
                    "sections_count": len(generated_plan.sections),
                }
            )
            
            return generated_plan
            
        except RuntimeError as e:
            logger.error(
                f"Plan generation failed",
                extra={"request_id": request_id, "error": str(e)},
                exc_info=True
            )
            span.set_attribute("error", True)
            span.set_attribute("error.type", "generation_failure")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Generation Error",
                    "message": f"Failed to generate composition plan: {str(e)}",
                    "request_id": request_id,
                }
            )
        
        except Exception as e:
            logger.error(
                f"Unexpected error during plan generation",
                extra={"request_id": request_id, "error": str(e)},
                exc_info=True
            )
            span.set_attribute("error", True)
            span.set_attribute("error.type", "unexpected")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred. Please contact support with the request ID.",
                    "request_id": request_id,
                }
            )
