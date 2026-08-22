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
    Generate a high-quality music prompt for ElevenLabs music_v2 model from two preset
    selections (project blueprint, delivery & control) plus the finetune that will
    render the track.

    The generated prompt is ready to be sent directly to the ElevenLabs music generation API.

    ## Input Parameters

    - **project_blueprint**: Defines the use case and structure (e.g., ad spot, podcast bed, video game loop)
    - **sound_profile**: Slug naming the ElevenLabs finetune used for rendering (e.g. `indie_dance`).
      Not a fixed preset list — any finetune slug is valid.
    - **finetune_id**: **Required.** Id of that finetune, from `GET /finetunes`. The server resolves it
      into genre metadata (name, primary_genre, tags) and the agent derives tempo, groove and
      instrumentation from it. Omitting it is a 422 — the genre is never guessed.
    - **delivery_and_control**: Defines workflow and output preferences (e.g., exploratory, balanced, blueprint-first)
    - **instrumental_only**: Optional override to force instrumental output regardless of blueprint
    - **user_narrative**: Optional freeform story/occasion/people details to guide lyrics and vocal tone.
      It governs lyrics and emotional intent, but never the genre — the finetune is authoritative there.

    If the finetune cannot be resolved (deleted, or ElevenLabs unreachable), the request still
    succeeds: a warning is logged and the agent infers the genre from the slug alone.

    ## Example Request

    ```json
    {
      "project_blueprint": "ad_brand_fast_hook",
      "sound_profile": "upbeat_pop",
      "finetune_id": "gduoyhnzn5nvb246gg7i",
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
                        "title": "Bright Pop Anthem",
                        "description": "A 30-second uplifting electronic ad spot with punchy synths and an immediate hook",
                        "request_id": "550e8400-e29b-41d4-a716-446655440000",
                        "timestamp": "2025-12-22T10:30:00Z",
                        "input_parameters": {
                            "project_blueprint": "ad_brand_fast_hook",
                            "sound_profile": "upbeat_pop",
                            "finetune_id": "gduoyhnzn5nvb246gg7i",
                            "delivery_and_control": "balanced_studio",
                            "instrumental_only": False,
                            "user_narrative": None
                        }
                    }
                }
            }
        },
        422: {"description": "Validation error - invalid input parameters, or 'finetune_id' missing"},
        500: {"description": "Internal server error during prompt generation"}
    }
)
async def generate_prompt(
    request_data: PromptGenerationRequest,
    request: Request,
) -> PromptGenerationResponse:
    """
    Generate a music prompt using the OpenAI Agents-based prompt generator.
    
    Users select presets for project type and delivery preferences, plus the finetune
    that will render the track. The server resolves that finetune's metadata and an AI
    agent with expert music direction knowledge derives the sonic attributes from it,
    producing a comprehensive, paste-ready prompt for the ElevenLabs music_v2 model.
    
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
        span.set_attribute("prompt.sound_profile", request_data.sound_profile)
        span.set_attribute("prompt.finetune_id", request_data.finetune_id)
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
                    "sound_profile": request_data.sound_profile,
                    "finetune_id": request_data.finetune_id,
                    "delivery_and_control": request_data.delivery_and_control.value,
                    "instrumental_only": request_data.instrumental_only,
                    "user_narrative": request_data.user_narrative,
                }
            )
            
            # Get the service instance
            service = get_prompt_generator_service()
            
            # Generate the prompt using the agent
            with tracer.start_as_current_span("agent_execution"):
                agent_output = await service.generate_prompt(request_data)
            
            # Build response
            response = PromptGenerationResponse(
                prompt=agent_output.prompt,
                title=agent_output.title,
                description=agent_output.description,
                request_id=request_id,
                timestamp=datetime.utcnow().isoformat(),
                input_parameters=request_data,
            )
            
            span.set_attribute("prompt.length", len(agent_output.prompt))
            span.set_attribute("success", True)
            
            logger.info(
                f"Successfully generated prompt",
                extra={
                    "request_id": request_id,
                    "prompt_length": len(agent_output.prompt),
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
