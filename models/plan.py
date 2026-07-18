"""
Request and response models for the composition plan endpoint.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class Chunk(BaseModel):
    """A chunk (section) of a music_v2 composition plan."""

    # Preserve any additional v2 fields (e.g. conditioning_ref, condition_strength)
    model_config = ConfigDict(extra="allow")

    text: str = Field(
        default="",
        description="Section marker and/or lyrics for this chunk (e.g. '[Intro]')"
    )
    positive_styles: list[str] = Field(
        default_factory=list,
        description="Style descriptors to include in this chunk"
    )
    negative_styles: list[str] = Field(
        default_factory=list,
        description="Style descriptors to avoid in this chunk"
    )
    duration_ms: int = Field(
        ...,
        description="Duration of this chunk in milliseconds"
    )
    context_adherence: Optional[str] = Field(
        default=None,
        description="How strictly the model should adhere to the surrounding context (e.g. 'high')"
    )


class CompositionPlanResponse(BaseModel):
    """Response model for a music_v2 composition plan."""

    chunks: list[Chunk] = Field(
        default_factory=list,
        description="List of chunks (sections) in the composition"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "chunks": [
                        {
                            "text": "[Intro]",
                            "positive_styles": [
                                "120 BPM",
                                "bright synthesizer hook",
                                "uplifting electronic pop",
                                "four-on-the-floor beat intro"
                            ],
                            "negative_styles": [],
                            "duration_ms": 6000,
                            "context_adherence": "high"
                        }
                    ]
                }
            ]
        }
    }


class PlanGenerationRequest(BaseModel):
    """Request model for generating a composition plan."""
    
    prompt: str = Field(
        ...,
        description="Text prompt describing the desired music composition"
    )
    music_length_ms: Optional[int] = Field(
        default=None,
        ge=1000,
        le=300000,
        description="Total length of the music in milliseconds (1-300 seconds). "
                    "If not provided, will be extracted from the prompt or default to 30 seconds."
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "prompt": "Create an uplifting electronic pop track with a catchy hook",
                    "music_length_ms": 10000
                },
                {
                    "prompt": "A dark ambient soundscape for a horror game",
                    "music_length_ms": 30000
                }
            ]
        }
    }


class PlanGenerationResponse(BaseModel):
    """Full response model for the plan generation endpoint."""
    
    plan: CompositionPlanResponse = Field(
        ...,
        description="The generated composition plan"
    )
    request_id: str = Field(
        ...,
        description="Unique request identifier for tracking"
    )
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp of generation"
    )
    input_prompt: str = Field(
        ...,
        description="The input prompt used to generate this plan"
    )
    music_length_ms: int = Field(
        ...,
        description="The requested music length in milliseconds"
    )
