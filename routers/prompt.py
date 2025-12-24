"""
API routes for music prompt generation.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Request, status, HTTPException
from opentelemetry import trace

from models.prompt import PromptGenerationRequest, PromptGenerationResponse
from services.prompt_generator import get_prompt_generator_service


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/prompt", tags=["Prompt Generation"])

# Get tracer for OpenTelemetry instrumentation
tracer = trace.get_tracer(__name__)


@router.post(
    "",
    response_model=PromptGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate music prompt",
    description="""
    Generate a high-quality music prompt for ElevenLabs music-1 model based on
    three preset selections: project blueprint, sound profile, and delivery & control.
    
    The generated prompt is ready to be sent directly to the ElevenLabs music generation API.
    
    ## Input Parameters
    
    - **project_blueprint**: Defines the use case and structure (e.g., ad spot, podcast bed, video game loop)
    - **sound_profile**: Defines the genre and sonic characteristics (e.g., bright pop, dark trap, lofi)
    - **delivery_and_control**: Defines workflow and output preferences (e.g., exploratory, balanced, blueprint-first)
    - **instrumental_only**: Optional override to force instrumental output regardless of blueprint
    - **user_narrative**: Optional freeform story/occasion/people details to guide lyrics and vocal tone
    
    ## Example Request
    
    ```json
    {
      "project_blueprint": "ad_brand_fast_hook",
      "sound_profile": "bright_pop_electro",
      "delivery_and_control": "balanced_studio",
      "instrumental_only": false,
      "user_narrative": null
    }
    ```
    """,
    responses={
        200: {
            "description": "Successfully generated music prompt",
            "content": {
                "application/json": {
                    "example": {
                        "prompt": "Create a 30-second uplifting electronic track...",
                        "request_id": "550e8400-e29b-41d4-a716-446655440000",
                        "timestamp": "2025-12-22T10:30:00Z",
                        "input_parameters": {
                            "project_blueprint": "ad_brand_fast_hook",
                            "sound_profile": "bright_pop_electro",
                            "delivery_and_control": "balanced_studio",
                            "instrumental_only": False,
                            "user_narrative": None
                        }
                    }
                }
            }
        },
        422: {"description": "Validation error - invalid input parameters"},
        500: {"description": "Internal server error during prompt generation"}
    }
)
async def generate_prompt(
    request_data: PromptGenerationRequest,
    request: Request,
) -> PromptGenerationResponse:
    """
    Generate a music prompt using the OpenAI Agents-based prompt generator.
    
    This endpoint uses the three-choice wizard approach where users select from
    predefined presets for project type, sound, and delivery preferences. The
    system then uses an AI agent with expert music direction knowledge to
    generate a comprehensive, paste-ready prompt for the ElevenLabs music-1 model.
    
    Args:
        request_data: The prompt generation request with preset selections
        request: The FastAPI request object (injected)
    
    Returns:
        A response containing the generated prompt and metadata
    
    Raises:
        HTTPException: If prompt generation fails
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    with tracer.start_as_current_span("generate_music_prompt") as span:
        # Add trace attributes
        span.set_attribute("prompt.project_blueprint", request_data.project_blueprint.value)
        span.set_attribute("prompt.sound_profile", request_data.sound_profile.value)
        span.set_attribute("prompt.delivery_control", request_data.delivery_and_control.value)
        span.set_attribute("prompt.instrumental_only", request_data.instrumental_only)
        span.set_attribute("request.id", request_id)
        
        try:
            # Log the full JSON request payload for debugging
            request_json = request_data.model_dump_json(indent=2)
            logger.info(
                f"Received prompt generation request - JSON payload:\n{request_json}",
                extra={
                    "request_id": request_id,
                    "project_blueprint": request_data.project_blueprint.value,
                    "sound_profile": request_data.sound_profile.value,
                    "delivery_and_control": request_data.delivery_and_control.value,
                    "instrumental_only": request_data.instrumental_only,
                    "user_narrative": request_data.user_narrative,
                }
            )
            
            # Get the service instance
            service = get_prompt_generator_service()
            
            # Generate the prompt using the agent
            with tracer.start_as_current_span("agent_execution"):
                generated_prompt = await service.generate_prompt(request_data)
            
            # Build response
            response = PromptGenerationResponse(
                prompt=generated_prompt,
                request_id=request_id,
                timestamp=datetime.utcnow().isoformat(),
                input_parameters=request_data,
            )
            
            span.set_attribute("prompt.length", len(generated_prompt))
            span.set_attribute("success", True)
            
            logger.info(
                f"Successfully generated prompt",
                extra={
                    "request_id": request_id,
                    "prompt_length": len(generated_prompt),
                }
            )
            
            return response
            
        except FileNotFoundError as e:
            logger.error(
                f"System prompt instructions file not found",
                extra={"request_id": request_id, "error": str(e)}
            )
            span.set_attribute("error", True)
            span.set_attribute("error.type", "configuration")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Configuration Error",
                    "message": "System prompt instructions not found. Please contact support.",
                    "request_id": request_id,
                }
            )
        
        except RuntimeError as e:
            logger.error(
                f"Prompt generation failed",
                extra={"request_id": request_id, "error": str(e)},
                exc_info=True
            )
            span.set_attribute("error", True)
            span.set_attribute("error.type", "generation_failure")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Generation Error",
                    "message": f"Failed to generate prompt: {str(e)}",
                    "request_id": request_id,
                }
            )
        
        except Exception as e:
            logger.error(
                f"Unexpected error during prompt generation",
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
