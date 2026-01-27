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
  "instrumental_only": false,
  "user_narrative": null
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

- **user_narrative** (optional, default: null): Freeform story, occasion, or people details to guide lyrics and vocal tone. When provided, the generated prompt will incorporate these details to shape lyrical content, vocal tone, and overall emotional intent.
  - Example: `"A love song for my wife Sarah on our 10th wedding anniversary. We met at a coffee shop in Seattle and she loves rainy days and acoustic guitar."`
  - **URL Support**: Can include URLs (http:// or https://) - the agent will automatically fetch and incorporate content from those URLs. See [Web Search Feature](#web-search-feature) below.

### Response

```json
{
  "prompt": "Create a 30-second uplifting electronic track in E major...",
  "title": "Bright Pop Anthem",
  "description": "A 30-second uplifting electronic ad spot with punchy synths and an immediate hook.",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-22T10:30:00Z",
  "input_parameters": {
    "project_blueprint": "ad_brand_fast_hook",
    "sound_profile": "bright_pop_electro",
    "delivery_and_control": "balanced_studio",
    "instrumental_only": false,
    "user_narrative": null
  }
}
```

#### Response Fields

- **prompt**: The generated music prompt (plain text) ready for ElevenLabs music-1 model
- **title**: AI-generated short, catchy title for the track (3-6 words)
- **description**: AI-generated clear, concise description of the track (1-2 sentences)
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
    "instrumental_only": true,
    "user_narrative": null
  }'
```

#### Using cURL (with user narrative)

```bash
curl -X POST http://localhost:8000/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "project_blueprint": "standalone_song_mini",
    "sound_profile": "indie_live_band",
    "delivery_and_control": "balanced_studio",
    "instrumental_only": false,
    "user_narrative": "A love song for my wife Sarah on our 10th wedding anniversary. We met at a coffee shop in Seattle and she loves rainy days and acoustic guitar."
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
                "instrumental_only": False,
                "user_narrative": None
            }
        )
        result = response.json()
        print(f"Title: {result['title']}")
        print(f"Description: {result['description']}")
        print(f"Generated prompt:\n{result['prompt']}")

asyncio.run(generate_prompt())
```

#### Using Python (httpx with user narrative)

```python
import httpx
import asyncio

async def generate_prompt_with_narrative():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/prompt",
            json={
                "project_blueprint": "standalone_song_mini",
                "sound_profile": "indie_live_band",
                "delivery_and_control": "balanced_studio",
                "instrumental_only": False,
                "user_narrative": "A birthday song for my daughter Emma who just turned 5. She loves unicorns, rainbows, and dancing in the garden."
            }
        )
        result = response.json()
        print(f"Title: {result['title']}")
        print(f"Description: {result['description']}")
        print(f"Generated prompt:\n{result['prompt']}")

asyncio.run(generate_prompt_with_narrative())
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
        "instrumental_only": True,
        "user_narrative": None
    }
)

result = response.json()
print(f"Title: {result['title']}")
print(f"Description: {result['description']}")
print(f"Generated prompt:\n{result['prompt']}")
```

#### Using cURL (with URL in user narrative)

```bash
curl -X POST http://localhost:8000/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "project_blueprint": "standalone_song_mini",
    "sound_profile": "indie_live_band",
    "delivery_and_control": "balanced_studio",
    "instrumental_only": false,
    "user_narrative": "Create a song inspired by this article about our company journey: https://example.com/our-story"
  }'
```

---

## Web Search Feature

The prompt generation agent has access to OpenAI's built-in **WebSearchTool**, enabling it to fetch and incorporate content from URLs included in the `user_narrative`.

### How It Works

1. **URL Detection**: When the agent detects URLs (http:// or https://) in the `user_narrative`, it automatically uses web search to retrieve relevant content.

2. **Content Extraction**: The agent extracts music-relevant information from the fetched content:
   - Themes, stories, and emotional tone
   - Names of people, places, or events
   - Brand voice or messaging (for product/company pages)
   - Event details (date, occasion, participants)
   - Mood or atmosphere descriptions

3. **Natural Integration**: The extracted information is woven into the music prompt as if the user had written it directly.

### Supported URL Types

| URL Type | What Gets Extracted |
|----------|---------------------|
| Article/Blog | Story, theme, emotional arc |
| Product/Company page | Brand personality, target audience, key messaging |
| Event page | Occasion details, mood, participants |
| Social media post | Narrative or story being shared |
| News article | Subject matter, tone, key facts |

### Example Use Cases

**Company anthem from About page:**
```json
{
  "project_blueprint": "standalone_song_mini",
  "sound_profile": "bright_pop_electro",
  "delivery_and_control": "balanced_studio",
  "user_narrative": "Create an uplifting company anthem based on our mission: https://example.com/about-us"
}
```

**Event music from invitation:**
```json
{
  "project_blueprint": "standalone_song_mini",
  "sound_profile": "indie_live_band",
  "delivery_and_control": "balanced_studio",
  "user_narrative": "Music for our wedding based on our story here: https://ourwedding.com/our-story"
}
```

**Product jingle from landing page:**
```json
{
  "project_blueprint": "ad_brand_fast_hook",
  "sound_profile": "bright_pop_electro",
  "delivery_and_control": "balanced_studio",
  "user_narrative": "Create a catchy jingle for this product: https://example.com/product/awesome-gadget"
}
```

### Combining URLs with Text

You can combine URLs with additional context:

```json
{
  "user_narrative": "A celebration song for our startup's 5th anniversary. Here's our journey: https://blog.startup.com/five-years. The mood should be triumphant but also grateful to our early supporters."
}
```

### Limitations

- **Inaccessible URLs**: If a URL cannot be fetched (404, blocked, etc.), the agent proceeds with whatever text context is available in the narrative.
- **Private content**: URLs requiring authentication (login-protected pages) cannot be accessed.
- **Rate limits**: Excessive URL fetching may be subject to rate limits.

---

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
- Enhanced output format with AI-generated title and description alongside the prompt
