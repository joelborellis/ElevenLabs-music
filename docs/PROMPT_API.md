# Music Prompt Generation API

This directory contains the implementation of the `/prompt` endpoint for generating high-quality music prompts for the ElevenLabs music-1 model.

## Architecture

The implementation follows FastAPI best practices with a clean separation of concerns:

```
.
├── models/              # Pydantic models for request/response validation
│   ├── __init__.py
│   └── prompt.py       # PromptGenerationRequest, PromptGenerationResponse
├── services/           # Business logic layer
│   ├── __init__.py
│   └── prompt_generator.py  # OpenAI Agents integration
├── routers/            # API route handlers
│   ├── __init__.py
│   └── prompt.py       # /prompt endpoint
└── main.py             # FastAPI application entry point
```

## Endpoint: POST /prompt

Generates a music prompt based on three preset selections using an AI agent with expert music direction knowledge.

### Request Body

```json
{
  "project_blueprint": "ad_brand_fast_hook",
  "sound_profile": "bright_pop_electro",
  "delivery_and_control": "balanced_studio",
  "instrumental_only": false
}
```

#### Parameters

- **project_blueprint** (required): Defines the use case and structure
  - `ad_brand_fast_hook` - 30s ad/brand spot with fast hook
  - `podcast_voiceover_loop` - 60s loopable podcast bed
  - `video_game_action_loop` - 90s loopable game music
  - `meditation_sleep` - Ambient meditation/sleep music
  - `standalone_song_mini` - 90s mini-song with structure

- **sound_profile** (required): Defines genre and sonic characteristics
  - `bright_pop_electro` - Uplifting electronic/EDM
  - `dark_trap_night` - Dark trap/hip-hop
  - `lofi_cozy` - Cozy lo-fi beats
  - `epic_cinematic` - Epic cinematic orchestral
  - `indie_live_band` - Indie live band sound

- **delivery_and_control** (required): Defines workflow preferences
  - `exploratory_iterate` - Exploratory with iteration
  - `balanced_studio` - Balanced studio approach
  - `blueprint_plan_first` - Blueprint planning first
  - `live_one_take` - Live one-take recording
  - `isolation_stems` - Isolated stem outputs

- **instrumental_only** (optional, default: false): Override to force instrumental output

### Response

```json
{
  "prompt": "Create a 30-second uplifting electronic track in E major...",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-22T10:30:00Z",
  "input_parameters": {
    "project_blueprint": "ad_brand_fast_hook",
    "sound_profile": "bright_pop_electro",
    "delivery_and_control": "balanced_studio",
    "instrumental_only": false
  }
}
```

#### Response Fields

- **prompt**: The generated music prompt (markdown string) ready for ElevenLabs music-1 model
- **request_id**: Unique identifier for tracking and debugging
- **timestamp**: ISO 8601 timestamp of generation
- **input_parameters**: Echo of the input parameters used

### Example Usage

#### Using cURL

```bash
curl -X POST http://localhost:8000/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "project_blueprint": "meditation_sleep",
    "sound_profile": "lofi_cozy",
    "delivery_and_control": "exploratory_iterate",
    "instrumental_only": true
  }'
```

#### Using Python (httpx)

```python
import httpx
import asyncio

async def generate_prompt():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/prompt",
            json={
                "project_blueprint": "ad_brand_fast_hook",
                "sound_profile": "bright_pop_electro",
                "delivery_and_control": "balanced_studio",
                "instrumental_only": False
            }
        )
        result = response.json()
        print(f"Generated prompt:\n{result['prompt']}")

asyncio.run(generate_prompt())
```

#### Using Python (requests)

```python
import requests

response = requests.post(
    "http://localhost:8000/prompt",
    json={
        "project_blueprint": "video_game_action_loop",
        "sound_profile": "epic_cinematic",
        "delivery_and_control": "balanced_studio",
        "instrumental_only": True
    }
)

result = response.json()
print(f"Generated prompt:\n{result['prompt']}")
```

## Features

### Clean Architecture
- **Models**: Pydantic schemas for type safety and validation
- **Services**: Business logic separated from API concerns
- **Routers**: Thin API layer focusing on HTTP concerns

### Observability
- OpenTelemetry tracing for all prompt generations
- Request ID tracking through the entire request lifecycle
- Structured logging with contextual information
- Custom span attributes for debugging

### Error Handling
- Comprehensive error handling with proper HTTP status codes
- Detailed error messages for debugging
- Request ID included in all error responses
- Graceful degradation with informative error messages

### Performance
- Lazy loading of system prompt instructions
- Singleton service pattern to reuse agent instances
- Async/await throughout for non-blocking operations

## Development

### Running the Application

```bash
# Development mode with auto-reload
uv run python main.py

# Or using uvicorn directly
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing the Endpoint

1. Start the application:
   ```bash
   uv run python main.py
   ```

2. Open the interactive API docs:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

3. Test the `/prompt` endpoint directly from the docs

### Environment Variables

The application uses `pydantic-settings` to load configuration from `.env` files:

```env
# OpenAI API Key (required for agents)
OPENAI_API_KEY=sk-...

# Application settings
APP_NAME=elevenlabs-music
APP_VERSION=0.1.0
ENVIRONMENT=development

# OpenTelemetry (optional)
OTEL_ENABLED=true
OTEL_EXPORTER_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=elevenlabs-music-api
```

## Migration from test_agents.py

The `/prompt` endpoint is based on the logic from `testing/test_agents.py` with these improvements:

1. **API-first**: Exposed as an HTTP endpoint instead of CLI wizard
2. **Production-ready**: Error handling, logging, and observability
3. **Type-safe**: Full Pydantic validation for inputs and outputs
4. **Scalable**: Service layer pattern allows easy extension
5. **Observable**: OpenTelemetry tracing throughout
6. **Documented**: OpenAPI/Swagger documentation auto-generated

The core logic remains the same:
- Uses the same system prompt instructions
- Same OpenAI Agents SDK integration
- Same three-choice wizard approach
- Same output format (markdown prompt string)
