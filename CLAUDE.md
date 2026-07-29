# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI-based REST API for AI-powered music generation using OpenAI Agents for prompt generation and ElevenLabs for music rendering. The core feature is a preset wizard that transforms two preset selections plus a chosen ElevenLabs finetune into professional music prompts.

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

1. **POST /prompt** - Converts the preset choices and chosen finetune (plus optional overrides) into a music prompt via an OpenAI Agent equipped with a web search tool. Resolves `finetune_id` against ElevenLabs to get real genre metadata for the agent
2. **POST /plan** - Generates composition plan from prompt via ElevenLabs API (`music_v2`)
3. **POST /render** - Renders audio from composition plan via ElevenLabs `compose_detailed` (`music_v2`); supports WebSocket streaming with progress updates. Pass the same `finetune_id` here that was used for `/prompt`

Supporting endpoint: **GET /finetunes** - proxies ElevenLabs' finetune list (cached, key stays server-side) so the client can populate the style picker that produces `sound_profile` + `finetune_id`.

### Key Directories

- `models/` - Pydantic schemas for all request/response types and enums for presets (includes `websocket.py` for streaming message types)
- `services/` - Business logic (prompt_generator, plan_generator, render_service)
- `routers/` - API endpoint handlers
- `prompts/` - System prompt templates for OpenAI Agents (critical for prompt quality)
- `docs/` - Per-endpoint API docs, preset guides, and WebSocket/middleware integration notes
- `testing/` - Test scripts (the core-pipeline ones are listed under Commands; other scripts are experimental)
- `output/music/` - Generated audio files (runtime)

### The Preset System

Two closed-set presets (Pydantic enums in `models/prompt.py`):

**Project Blueprint** (use case): ad_brand_fast_hook, podcast_voiceover_loop, video_game_action_loop, meditation_sleep, standalone_song_mini

**Delivery & Control** (workflow): exploratory_iterate, balanced_studio, blueprint_plan_first, live_one_take, isolation_stems

Genre is **not** a preset. It comes from an ElevenLabs finetune the user picks (via `GET /finetunes`):

- `sound_profile` (str, required) - slug naming the finetune, e.g. `indie_dance`. Open-ended: any slug is valid, there is no enum
- `finetune_id` (str, **required**) - the finetune's id. Missing it is a `422`; the genre is never guessed

`services/prompt_generator.py` resolves `finetune_id` server-side via `FinetuneService.get_finetune()` and merges the resulting `finetune_context` (`name`, `primary_genre`, `tags`) into the JSON handed to the agent. The agent *derives* the eleven sound attributes from that metadata rather than looking them up. If the finetune can't be resolved, a warning is logged and the agent infers the genre from the slug alone — the request still succeeds. `finetune_context` is deliberately not on `PromptGenerationRequest`, which is echoed back as `input_parameters`.

Two further optional inputs on `PromptGenerationRequest`:

- `instrumental_only` (bool, default `false`) - forces instrumental-only output regardless of the project blueprint
- `user_narrative` (str, optional) - freeform story/occasion/people details used to guide lyrics and vocal tone. It governs lyrics and emotion but **never** genre — the finetune is authoritative there

The system prompt forbids naming the finetune (its name, slug, or the words "finetune"/"style model") anywhere in the generated prompt, title, or description.

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
