"""
Request and response models for the music render endpoint.
"""

from typing import Optional
from pydantic import BaseModel, Field, model_validator

from models.plan import Chunk


class RenderRequest(BaseModel):
    """Request model for rendering music via ElevenLabs ``compose_detailed``.

    Provide EITHER ``prompt`` (text-to-music) OR ``chunks`` (a ``music_v2``
    composition plan) — the two are mutually exclusive, matching the ElevenLabs
    API contract. Every other field maps directly to a ``compose_detailed`` body
    parameter (with project-specific defaults) so all supported options can be
    passed through. ``seed`` and ``respect_sections_durations`` are intentionally
    omitted because the pinned ElevenLabs SDK (2.58.0) does not support them.
    """

    # --- Generation source (mutually exclusive) ---
    prompt: Optional[str] = Field(
        default=None,
        description="Simple text prompt to generate a song from. Mutually exclusive with 'chunks'."
    )
    chunks: list[Chunk] = Field(
        default_factory=list,
        description="Composition plan sections (music_v2). Mutually exclusive with 'prompt'."
    )

    # --- Prompt-mode only ---
    music_length_ms: Optional[int] = Field(
        default=None,
        ge=3000,
        le=600000,
        description="Length of the song in milliseconds (3000-600000). Only used together with 'prompt'."
    )

    # --- compose_detailed body parameters (project defaults) ---
    model_id: str = Field(
        default="music_v2",
        description="ElevenLabs generation model: 'music_v1' or 'music_v2'."
    )
    force_instrumental: bool = Field(
        default=False,
        description="If true, guarantees that the generated song will be instrumental."
    )
    store_for_inpainting: bool = Field(
        default=False,
        description="Whether to store the generated song to allow later inpainting."
    )
    with_timestamps: bool = Field(
        default=False,
        description="Whether to return word-level timestamps for the generated song."
    )
    sign_with_c2pa: bool = Field(
        default=False,
        description="Whether to sign the generated song with C2PA provenance metadata."
    )

    # --- Query parameter ---
    output_format: Optional[str] = Field(
        default=None,
        description="Audio output format (e.g. 'mp3_44100_128', 'pcm_44100'). Leave null to let the API choose."
    )

    # --- Local only (NOT sent to ElevenLabs) ---
    title: Optional[str] = Field(
        default=None,
        description="Optional title (from /prompt response). Used only to name the saved output file."
    )

    @model_validator(mode="after")
    def _validate_source(self) -> "RenderRequest":
        """Enforce the prompt/composition-plan mutual exclusivity contract."""
        has_prompt = bool(self.prompt and self.prompt.strip())
        has_chunks = bool(self.chunks)

        if has_prompt and has_chunks:
            raise ValueError("Provide either 'prompt' or 'chunks', not both.")
        if not has_prompt and not has_chunks:
            raise ValueError("Provide either 'prompt' or 'chunks'.")
        if self.music_length_ms is not None and not has_prompt:
            raise ValueError("'music_length_ms' can only be used together with 'prompt'.")

        return self

    def to_compose_kwargs(self) -> dict:
        """Build the keyword arguments for ``music.compose_detailed``.

        Includes only the source that was provided (prompt vs. composition plan)
        and omits ``output_format`` when unset so the API default applies.
        ``title`` is intentionally excluded — it is a local-only field.
        """
        kwargs: dict = {
            "model_id": self.model_id,
            "force_instrumental": self.force_instrumental,
            "store_for_inpainting": self.store_for_inpainting,
            "with_timestamps": self.with_timestamps,
            "sign_with_c2pa": self.sign_with_c2pa,
        }

        if self.output_format is not None:
            kwargs["output_format"] = self.output_format

        if self.prompt and self.prompt.strip():
            kwargs["prompt"] = self.prompt
            if self.music_length_ms is not None:
                kwargs["music_length_ms"] = self.music_length_ms
        else:
            kwargs["composition_plan"] = {
                "chunks": [chunk.model_dump() for chunk in self.chunks]
            }

        return kwargs

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Bright Pop Anthem",
                    "chunks": [
                        {
                            "text": "[Intro]",
                            "positive_styles": [
                                "120 BPM",
                                "clean electric guitar riff",
                                "minimal instrumentation"
                            ],
                            "negative_styles": [
                                "full band",
                                "vocals"
                            ],
                            "duration_ms": 6000,
                            "context_adherence": "high"
                        }
                    ],
                    "model_id": "music_v2",
                    "force_instrumental": False,
                    "with_timestamps": False
                },
                {
                    "title": "Quick Prompt Track",
                    "prompt": "An upbeat 30-second bright pop-electro ad hook at 120 BPM in E major.",
                    "music_length_ms": 30000,
                    "model_id": "music_v2",
                    "force_instrumental": True,
                    "output_format": "mp3_44100_128"
                }
            ]
        }
    }


class RenderResponse(BaseModel):
    """Response model for the render endpoint."""

    id: str = Field(
        ...,
        description="Unique render identifier (primary handle for download/stream)"
    )
    filename: str = Field(
        ...,
        description="The filename of the generated audio file"
    )
    file_path: Optional[str] = Field(
        default=None,
        description="Canonical storage URL/URI where the audio was saved (blob URL or file URI)"
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
    duration_ms: Optional[int] = Field(
        default=None,
        description="Total duration of the generated audio in milliseconds"
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
