"""
Request and response models for the music render endpoint.
"""

from typing import Optional
from pydantic import BaseModel, Field

from models.plan import Section


class RenderRequest(BaseModel):
    """Request model for rendering music from a composition plan."""

    title: Optional[str] = Field(
        default=None,
        description="Optional title for the output file (from /prompt response). If provided, used to name the output file."
    )
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
                    "title": "Bright Pop Anthem",
                    "positive_global_styles": [
                        "indie pop",
                        "indie rock",
                        "uplifting",
                        "95 bpm"
                    ],
                    "negative_global_styles": [
                        "heavy reverb",
                        "electronic drums"
                    ],
                    "sections": [
                        {
                            "section_name": "Intro",
                            "positive_local_styles": [
                                "clean electric guitar riff",
                                "minimal instrumentation"
                            ],
                            "negative_local_styles": [
                                "full band",
                                "vocals"
                            ],
                            "duration_ms": 4000,
                            "lines": [],
                            "source_from": None
                        }
                    ]
                }
            ]
        }
    }


class RenderResponse(BaseModel):
    """Response model for the render endpoint."""
    
    filename: str = Field(
        ...,
        description="The filename of the generated audio file"
    )
    file_path: str = Field(
        ...,
        description="The local path where the file was saved"
    )
    download_url: str = Field(
        ...,
        description="URL to download the generated audio file"
    )
    stream_url: Optional[str] = Field(
        default=None,
        description="URL to stream the generated audio file for playback"
    )
    content_type: str = Field(
        default="audio/mpeg",
        description="MIME type of the audio file"
    )
    file_size_bytes: int = Field(
        ...,
        description="Size of the audio file in bytes"
    )
    composition_plan: Optional[dict] = Field(
        default=None,
        description="The composition plan with any modifications from the API"
    )
    song_metadata: Optional[dict] = Field(
        default=None,
        description="Metadata about the generated song"
    )
    request_id: str = Field(
        ...,
        description="Unique request identifier for tracking"
    )
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp of generation"
    )
