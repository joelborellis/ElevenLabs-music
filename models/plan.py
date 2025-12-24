"""
Request and response models for the composition plan endpoint.
"""

from typing import Optional
from pydantic import BaseModel, Field


class Section(BaseModel):
    """A section of the composition plan."""
    
    section_name: str = Field(
        ...,
        description="Name of the section (e.g., 'Instant Hook', 'Quick Build')"
    )
    positive_local_styles: list[str] = Field(
        default_factory=list,
        description="Style descriptors to include in this section"
    )
    negative_local_styles: list[str] = Field(
        default_factory=list,
        description="Style descriptors to avoid in this section"
    )
    duration_ms: int = Field(
        ...,
        description="Duration of this section in milliseconds"
    )
    lines: list[str] = Field(
        default_factory=list,
        description="Lyric lines for this section"
    )
    source_from: Optional[str] = Field(
        default=None,
        description="Source reference for this section"
    )


class CompositionPlanResponse(BaseModel):
    """Response model for the composition plan."""
    
    positive_global_styles: list[str] = Field(
        default_factory=list,
        description="Global style descriptors to include in the composition"
    )
    negative_global_styles: list[str] = Field(
        default_factory=list,
        description="Global style descriptors to avoid in the composition"
    )
    sections: list[Section] = Field(
        default_factory=list,
        description="List of sections in the composition"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "positive_global_styles": [
                        "electronic pop",
                        "high-energy",
                        "EDM",
                        "uplifting",
                        "euphoric",
                        "122 bpm",
                        "E major",
                        "instrumental",
                        "radio-polished production",
                        "4/4 time signature"
                    ],
                    "negative_global_styles": [
                        "vocals",
                        "lyrics",
                        "slow tempo",
                        "dark",
                        "acoustic",
                        "lo-fi"
                    ],
                    "sections": [
                        {
                            "section_name": "Instant Hook",
                            "positive_local_styles": [
                                "immediate start",
                                "punchy drums",
                                "bright synth chords"
                            ],
                            "negative_local_styles": [
                                "slow build-up",
                                "vocals"
                            ],
                            "duration_ms": 3000,
                            "lines": [],
                            "source_from": None
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
    music_length_ms: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        description="Total length of the music in milliseconds (1-300 seconds)"
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
