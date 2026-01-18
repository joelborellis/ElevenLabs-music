# ElevenLabs Music Prompt Generator API

A production-ready FastAPI application that generates high-quality music prompts for the ElevenLabs music-1 model using OpenAI Agents.

## Features

- 🎵 **Three-Choice Wizard**: Intuitive preset-based prompt generation
- 🤖 **AI-Powered**: Uses OpenAI Agents with expert music direction knowledge
- 🚀 **Production-Ready**: Full observability with OpenTelemetry
- 📝 **Type-Safe**: Comprehensive Pydantic validation
- 🔍 **Observable**: Request tracing, structured logging, metrics
- 📚 **Well-Documented**: Auto-generated OpenAPI/Swagger docs

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- OpenAI API key

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd ElevenLabs-music
   ```

2. Create a `.env` file with your OpenAI API key:
   ```bash
   echo "OPENAI_API_KEY=sk-your-api-key-here" > .env
   ```

3. Install dependencies:
   ```bash
   # Using uv (recommended)
   uv sync

   # Or using pip
   pip install -r requirements.txt
   ```

### Running the Application

```bash
# Development mode with auto-reload
uv run python main.py

# Or using uvicorn directly
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## API Usage

### POST /prompt

Generate a music prompt using three preset selections.

**Request:**
```bash
curl -X POST http://localhost:8000/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "project_blueprint": "ad_brand_fast_hook",
    "sound_profile": "bright_pop_electro",
    "delivery_and_control": "balanced_studio",
    "instrumental_only": false
  }'
```

**Response:**
```json
{
  "prompt": "Create a 30-second uplifting electronic track in E major at 120 BPM...",
  "title": "Bright Pop Anthem",
  "description": "A 30-second uplifting electronic ad spot with punchy synths and an immediate hook.",
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

The response includes an AI-generated `title` and `description` based on the generated prompt, making it easy to catalog and identify tracks.

### POST /plan

Generate a composition plan from a text prompt using the ElevenLabs music API.

**Request:**
```bash
curl -X POST http://localhost:8000/plan \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create an uplifting electronic pop track with a catchy hook",
    "music_length_ms": 30000
  }'
```

**Request Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | Text prompt describing the desired music composition |
| `music_length_ms` | integer | No | 30000 | Total length in milliseconds (1000-300000) |

**Response:**
```json
{
  "positive_global_styles": ["electronic pop", "uplifting", "high-energy", "122 bpm"],
  "negative_global_styles": ["dark", "slow tempo", "acoustic"],
  "sections": [
    {
      "section_name": "Instant Hook",
      "positive_local_styles": ["immediate start", "punchy drums", "bright synth chords"],
      "negative_local_styles": ["slow build-up"],
      "duration_ms": 3000,
      "lines": [],
      "source_from": null
    }
  ]
}
```

### POST /render

Render music from a composition plan using the ElevenLabs API.

**Request:**
```bash
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{
    "positive_global_styles": ["indie pop", "uplifting", "95 bpm"],
    "negative_global_styles": ["heavy reverb", "electronic drums"],
    "sections": [
      {
        "section_name": "Intro",
        "positive_local_styles": ["clean electric guitar riff", "minimal instrumentation"],
        "negative_local_styles": ["full band", "vocals"],
        "duration_ms": 4000,
        "lines": [],
        "source_from": null
      }
    ]
  }'
```

**Request Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `positive_global_styles` | array[string] | No | Global style descriptors to include |
| `negative_global_styles` | array[string] | No | Global style descriptors to avoid |
| `sections` | array[Section] | No | List of composition sections |

**Section Object:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `section_name` | string | Yes | Name of the section (e.g., "Intro", "Verse") |
| `positive_local_styles` | array[string] | No | Style descriptors for this section |
| `negative_local_styles` | array[string] | No | Styles to avoid in this section |
| `duration_ms` | integer | Yes | Duration in milliseconds |
| `lines` | array[string] | No | Lyric lines for this section |
| `source_from` | string | No | Source reference for this section |

**Response:**
```json
{
  "filename": "track_abc123.mp3",
  "file_path": "/output/music/track_abc123.mp3",
  "download_url": "/render/download/track_abc123.mp3",
  "content_type": "audio/mpeg",
  "file_size_bytes": 524288,
  "composition_plan": { ... },
  "song_metadata": { ... },
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-22T10:30:00"
}
```

### GET /render/download/{filename}

Download a previously rendered audio file.

```bash
curl -O http://localhost:8000/render/download/track_abc123.mp3
```

### GET /render/stream/{filename}

Stream a previously rendered audio file for playback.

```bash
curl http://localhost:8000/render/stream/track_abc123.mp3
```

### Available Presets

#### Project Blueprint (use case & structure)
- `ad_brand_fast_hook` - 30s ad/brand spot
- `podcast_voiceover_loop` - 60s loopable podcast bed
- `video_game_action_loop` - 90s loopable game music
- `meditation_sleep` - Ambient meditation/sleep
- `standalone_song_mini` - 90s mini-song

#### Sound Profile (genre & sonic characteristics)
- `bright_pop_electro` - Uplifting electronic/EDM
- `dark_trap_night` - Dark trap/hip-hop
- `lofi_cozy` - Cozy lo-fi beats
- `epic_cinematic` - Epic cinematic orchestral
- `indie_live_band` - Indie live band sound

#### Delivery & Control (workflow preferences)
- `exploratory_iterate` - Exploratory with iteration
- `balanced_studio` - Balanced studio approach
- `blueprint_plan_first` - Blueprint planning first
- `live_one_take` - Live one-take recording
- `isolation_stems` - Isolated stem outputs

For detailed API documentation, see [docs/PROMPT_API.md](docs/PROMPT_API.md).

## Project Structure

```
.
├── main.py                 # FastAPI application entry point
├── models/                 # Pydantic models
│   ├── __init__.py
│   ├── prompt.py          # Prompt request/response models
│   ├── plan.py            # Composition plan models
│   └── render.py          # Render request/response models
├── services/              # Business logic
│   ├── __init__.py
│   ├── prompt_generator.py  # OpenAI Agents integration
│   ├── plan_generator.py    # ElevenLabs plan generation
│   └── render_service.py    # ElevenLabs music rendering
├── routers/               # API routes
│   ├── __init__.py
│   ├── prompt.py          # /prompt endpoint
│   ├── plan.py            # /plan endpoint
│   └── render.py          # /render endpoint
├── prompts/               # System prompt templates
│   └── system_prompt_eleven_music_3choice_wizard_prompt_architect_NEW.md
├── output/                # Generated audio files
│   └── music/             # Rendered music files
├── testing/               # Test scripts
│   ├── test_agents.py            # Original CLI wizard
│   ├── test_prompt_endpoint.py   # API endpoint tests
│   ├── test_plan_endpoint.py     # Plan endpoint tests
│   ├── test_render_endpoint.py   # Render endpoint tests
│   └── ...
├── docs/                  # Documentation
│   ├── PROMPT_API.md      # Prompt API docs
│   ├── PLAN_API.md        # Plan API docs
│   └── RENDER_API.md      # Render API docs
├── pyproject.toml         # Project dependencies
└── README.md              # This file
```

## Development

### Testing

Test the endpoint using the provided test script:

```bash
# Test single request
uv run python testing/test_prompt_endpoint.py

# Test multiple combinations
uv run python testing/test_prompt_endpoint.py --all
```

### Code Quality

The project follows FastAPI best practices:

- **Separation of Concerns**: Models, services, and routes are separate
- **Type Safety**: Full Pydantic validation throughout
- **Error Handling**: Comprehensive error handling with proper HTTP codes
- **Logging**: Structured logging with contextual information
- **Observability**: OpenTelemetry tracing and metrics

### Environment Variables

Create a `.env` file with the following variables:

```env
# Required
OPENAI_API_KEY=sk-...

# Optional (defaults shown)
APP_NAME=elevenlabs-music
APP_VERSION=0.1.0
ENVIRONMENT=development

# OpenTelemetry
OTEL_ENABLED=true
OTEL_EXPORTER_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=elevenlabs-music-api

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

## Architecture

### Request Flow

1. **Client** sends POST request to `/prompt` with preset selections
2. **Router** (`routers/prompt.py`) validates request with Pydantic
3. **Service** (`services/prompt_generator.py`) loads system prompt and creates agent
4. **Agent** (OpenAI Agents SDK) generates music prompt based on presets
5. **Router** returns formatted response with metadata

### Key Components

- **Models** (`models/prompt.py`): Type-safe request/response schemas
- **Service** (`services/prompt_generator.py`): Business logic and agent management
- **Router** (`routers/prompt.py`): HTTP endpoint handler with observability
- **System Prompt**: Expert music direction instructions for the AI agent

### Observability

The application includes comprehensive observability:

- **Tracing**: OpenTelemetry spans for all operations
- **Logging**: Structured JSON logs with request context
- **Metrics**: Request counters and error tracking
- **Request IDs**: Unique IDs for tracking requests end-to-end

## Deployment

### Docker (Coming Soon)

```bash
docker build -t elevenlabs-music-api .
docker run -p 8000:8000 --env-file .env elevenlabs-music-api
```

### Cloud Deployment

The application is ready for deployment to:
- AWS ECS/Fargate
- Google Cloud Run
- Azure Container Apps
- Kubernetes

Health check endpoints:
- `/health` - Comprehensive health check
- `/ready` - Readiness probe
- `/alive` - Liveness probe

## Migration from CLI

This API is based on the original CLI wizard in `testing/test_agents.py` with these enhancements:

- ✅ RESTful API instead of interactive CLI
- ✅ Production-ready error handling
- ✅ OpenTelemetry observability
- ✅ Type-safe validation
- ✅ Auto-generated API documentation
- ✅ Clean architecture with separation of concerns

The core logic and system prompts remain unchanged.

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]
