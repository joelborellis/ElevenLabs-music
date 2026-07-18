# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI-based REST API for AI-powered music generation using OpenAI Agents for prompt generation and ElevenLabs for music rendering. The core feature is a "three-choice" preset wizard system that transforms user selections into professional music prompts.

## Commands

```bash
# Install dependencies
uv sync

# Run development server (auto-reload on port 8000)
uv run python main.py

# Run production server
uv run uvicorn main:app --host 0.0.0.0 --port 8000

# Run tests
uv run python testing/test_prompt_endpoint.py
uv run python testing/test_plan_endpoint.py
uv run python testing/test_render_endpoint.py
uv run python testing/test_render_websocket.py
```

## Architecture

### Request Flow

```
Client → FastAPI Router → Pydantic Validation → Service Layer → External API → Response
```

### Three-Stage Music Generation Pipeline

1. **POST /prompt** - Converts the preset choices (plus optional overrides) into a music prompt via an OpenAI Agent equipped with a web search tool
2. **POST /plan** - Generates composition plan from prompt via ElevenLabs API (`music_v2`)
3. **POST /render** - Renders audio from composition plan via ElevenLabs `compose_detailed` (`music_v2`); supports WebSocket streaming with progress updates

### Key Directories

- `models/` - Pydantic schemas for all request/response types and enums for presets (includes `websocket.py` for streaming message types)
- `services/` - Business logic (prompt_generator, plan_generator, render_service)
- `routers/` - API endpoint handlers
- `prompts/` - System prompt templates for OpenAI Agents (critical for prompt quality)
- `docs/` - Per-endpoint API docs, preset guides, and WebSocket/middleware integration notes
- `testing/` - Test scripts (the core-pipeline ones are listed under Commands; other scripts are experimental)
- `output/music/` - Generated audio files (runtime)

### The Three-Choice Preset System

Users select one from each category:

**Project Blueprint** (use case): ad_brand_fast_hook, podcast_voiceover_loop, video_game_action_loop, meditation_sleep, standalone_song_mini

**Sound Profile** (genre): bright_pop_electro, dark_trap_night, lofi_cozy, epic_cinematic, indie_live_band

**Delivery & Control** (workflow): exploratory_iterate, balanced_studio, blueprint_plan_first, live_one_take, isolation_stems

In addition to the three presets, the `/prompt` request (`PromptGenerationRequest`) accepts two optional inputs:

- `instrumental_only` (bool, default `false`) - forces instrumental-only output regardless of the project blueprint
- `user_narrative` (str, optional) - freeform story/occasion/people details used to guide lyrics and vocal tone

### External Integrations

- **OpenAI Agents SDK** - Prompt generation with system prompt from `prompts/generate_music_prompt.md`; the agent is configured with `WebSearchTool` and returns structured output (prompt, title, description)
- **ElevenLabs API** - Composition planning (`music.composition_plan.create`) and music rendering (`music.compose_detailed`), both pinned to `model_id="music_v2"`
- **OpenTelemetry** - Distributed tracing (enabled by default; configured via env vars)

## Environment Variables

Required:
- `OPENAI_API_KEY` - OpenAI API key for Agents (validated at startup in `main.py`; the app refuses to boot without it)
- `ELEVENLABS_API_KEY` - ElevenLabs API key for planning/rendering (checked lazily when a service first initializes, not at startup)

Optional:
- `ENVIRONMENT` - 'development' or 'production'
- `OTEL_ENABLED` - Enable OpenTelemetry observability (defaults to enabled)

## API Documentation

Interactive docs available at `http://localhost:8000/docs` when server is running.
