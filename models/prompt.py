"""
Request and response models for the music prompt generation endpoint.
"""

from enum import Enum
from pydantic import BaseModel, Field


class ProjectBlueprint(str, Enum):
    """Project blueprint presets defining the use case and structure."""
    
    AD_BRAND_FAST_HOOK = "ad_brand_fast_hook"
    PODCAST_VOICEOVER_LOOP = "podcast_voiceover_loop"
    VIDEO_GAME_ACTION_LOOP = "video_game_action_loop"
    MEDITATION_SLEEP = "meditation_sleep"
    STANDALONE_SONG_MINI = "standalone_song_mini"


class DeliveryAndControl(str, Enum):
    """Delivery and control presets defining workflow and output preferences."""
    
    EXPLORATORY_ITERATE = "exploratory_iterate"
    BALANCED_STUDIO = "balanced_studio"
    BLUEPRINT_PLAN_FIRST = "blueprint_plan_first"
    LIVE_ONE_TAKE = "live_one_take"
    ISOLATION_STEMS = "isolation_stems"


class PromptGenerationRequest(BaseModel):
    """Request model for generating music prompts."""
    
    project_blueprint: ProjectBlueprint = Field(
        ...,
        description="The project blueprint preset defining use case and structure"
    )
    sound_profile: str = Field(
        ...,
        min_length=1,
        description="Slug naming the ElevenLabs finetune used for rendering (e.g. 'indie_dance'). "
                    "Open-ended: new finetunes appear without any change here."
    )
    finetune_id: str = Field(
        ...,
        min_length=1,
        description="Id of the finetune named by 'sound_profile'. Resolved server-side into genre "
                    "metadata that drives the prompt. Get ids from GET /finetunes."
    )
    delivery_and_control: DeliveryAndControl = Field(
        ...,
        description="The delivery and control preset defining workflow preferences"
    )
    instrumental_only: bool = Field(
        default=False,
        description="Override to force instrumental-only output regardless of project blueprint"
    )
    user_narrative: str | None = Field(
        default=None,
        description="Freeform story/occasion/people details to guide lyrics and vocal tone"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "project_blueprint": "ad_brand_fast_hook",
                    "sound_profile": "upbeat_pop",
                    "finetune_id": "gduoyhnzn5nvb246gg7i",
                    "delivery_and_control": "balanced_studio",
                    "instrumental_only": False,
                    "user_narrative": None
                },
                {
                    "project_blueprint": "standalone_song_mini",
                    "sound_profile": "golden_hour_indie_guitar",
                    "finetune_id": "v1hamfp8dn8witowl0ku",
                    "delivery_and_control": "balanced_studio",
                    "instrumental_only": False,
                    "user_narrative": "A love song for my wife Sarah on our 10th wedding anniversary. We met at a coffee shop in Seattle and she loves rainy days and acoustic guitar."
                },
                {
                    "project_blueprint": "meditation_sleep",
                    "sound_profile": "relaxing_ambient",
                    "finetune_id": "c8gueokxdvc0websp3mh",
                    "delivery_and_control": "exploratory_iterate",
                    "instrumental_only": True,
                    "user_narrative": None
                }
            ]
        }
    }


class AgentPromptOutput(BaseModel):
    """Structured output from the prompt generator agent."""
    
    prompt: str = Field(
        ...,
        description="The generated music prompt ready for ElevenLabs music_v2 model"
    )
    title: str = Field(
        ...,
        description="A short, catchy title for the generated music track (3-6 words max)"
    )
    description: str = Field(
        ...,
        description="A clear, concise description of the track (1-2 sentences)"
    )


class PromptGenerationResponse(BaseModel):
    """Response model for generated music prompts."""
    
    prompt: str = Field(
        ...,
        description="The generated music prompt ready for ElevenLabs music_v2 model"
    )
    title: str | None = Field(
        default=None,
        description="Title for the generated music track"
    )
    description: str | None = Field(
        default=None,
        description="Description for the generated music track"
    )
    request_id: str = Field(
        ...,
        description="Unique request identifier for tracking"
    )
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp of generation"
    )
    input_parameters: PromptGenerationRequest = Field(
        ...,
        description="The input parameters used to generate this prompt"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
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
                        "instrumental_only": False
                    }
                }
            ]
        }
    }
