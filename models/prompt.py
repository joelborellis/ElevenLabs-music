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


class SoundProfile(str, Enum):
    """Sound profile presets defining the genre and sonic characteristics."""
    
    BRIGHT_POP_ELECTRO = "bright_pop_electro"
    DARK_TRAP_NIGHT = "dark_trap_night"
    LOFI_COZY = "lofi_cozy"
    EPIC_CINEMATIC = "epic_cinematic"
    INDIE_LIVE_BAND = "indie_live_band"


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
    sound_profile: SoundProfile = Field(
        ...,
        description="The sound profile preset defining genre and sonic characteristics"
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
                    "sound_profile": "bright_pop_electro",
                    "delivery_and_control": "balanced_studio",
                    "instrumental_only": False,
                    "user_narrative": None
                },
                {
                    "project_blueprint": "standalone_song_mini",
                    "sound_profile": "indie_live_band",
                    "delivery_and_control": "balanced_studio",
                    "instrumental_only": False,
                    "user_narrative": "A love song for my wife Sarah on our 10th wedding anniversary. We met at a coffee shop in Seattle and she loves rainy days and acoustic guitar."
                },
                {
                    "project_blueprint": "meditation_sleep",
                    "sound_profile": "lofi_cozy",
                    "delivery_and_control": "exploratory_iterate",
                    "instrumental_only": True,
                    "user_narrative": None
                }
            ]
        }
    }


class PromptGenerationResponse(BaseModel):
    """Response model for generated music prompts."""
    
    prompt: str = Field(
        ...,
        description="The generated music prompt ready for ElevenLabs music-1 model"
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
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    "timestamp": "2025-12-22T10:30:00Z",
                    "input_parameters": {
                        "project_blueprint": "ad_brand_fast_hook",
                        "sound_profile": "bright_pop_electro",
                        "delivery_and_control": "balanced_studio",
                        "instrumental_only": False
                    }
                }
            ]
        }
    }
