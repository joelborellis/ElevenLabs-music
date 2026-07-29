# ElevenLabs Music Prompt Generator API

A production-ready FastAPI application that generates high-quality music prompts for the ElevenLabs music_v2 model using OpenAI Agents.

## Features

- 🎵 **Preset Wizard**: Intuitive preset-based prompt generation
- 🤖 **AI-Powered**: Uses OpenAI Agents with expert music direction knowledge
- 🎚️ **Finetune-Driven**: The chosen ElevenLabs finetune supplies the genre for the prompt *and* renders the audio
- 🔌 **WebSocket Streaming**: Real-time render progress updates
- 💾 **Persistent Storage**: Rendered audio in local disk or Azure Blob, metadata in SQLite/Postgres
- 🚀 **Production-Ready**: Full observability with OpenTelemetry
- 📝 **Type-Safe**: Comprehensive Pydantic validation
- 🔍 **Observable**: Request tracing, structured logging, metrics
- 📚 **Well-Documented**: Auto-generated OpenAPI/Swagger docs

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- OpenAI API key (required at startup)
- ElevenLabs API key (required for `/plan`, `/render`, and `/finetunes`)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd ElevenLabs-music
   ```

2. Create a `.env` file with your API keys:
   ```bash
   printf 'OPENAI_API_KEY=sk-your-api-key-here\nELEVENLABS_API_KEY=your-elevenlabs-key\n' > .env
   ```

3. Install dependencies:
   ```bash
   uv sync
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

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/prompt` | Generate a music prompt from the presets + chosen finetune |
| `POST` | `/plan` | Generate a `music_v2` composition plan from a prompt |
| `POST` | `/render` | Render audio from a prompt or a composition plan |
| `WS` | `/render/ws` | Render with real-time progress updates |
| `GET` | `/render/download/{identifier}` | Download rendered audio |
| `GET` | `/render/stream/{identifier}` | Stream rendered audio for playback |
| `GET` | `/finetunes` | List ElevenLabs music finetunes for a picker |
| `GET` | `/` | API info and endpoint index |
| `GET` | `/health` | Health check with dependency status |
| `GET` | `/ready` | Readiness probe |
| `GET` | `/alive` | Liveness probe |
| `GET` | `/stream-example` | SSE demo endpoint |

## API Usage

### POST /prompt

Generate a music prompt using three preset selections.

**Request:**
```bash
curl -X POST http://localhost:8000/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "project_blueprint": "ad_brand_fast_hook",
    "sound_profile": "upbeat_pop",
    "finetune_id": "gduoyhnzn5nvb246gg7i",
    "delivery_and_control": "balanced_studio",
    "instrumental_only": false,
    "user_narrative": null
  }'
```

**Request Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_blueprint` | enum | Yes | - | Use case and structure (see [Available Presets](#available-presets)) |
| `sound_profile` | string | Yes | - | Slug naming the finetune that will render the track (e.g. `indie_dance`). Open-ended, not an enum |
| `finetune_id` | string | Yes | - | That finetune's id, from `GET /finetunes`. Resolved server-side for genre metadata; omitting it is a `422` |
| `delivery_and_control` | enum | Yes | - | Workflow and strictness preferences |
| `instrumental_only` | boolean | No | `false` | Force instrumental output regardless of blueprint |
| `user_narrative` | string | No | `null` | Freeform story/occasion/people details that drive lyrics and vocal tone |

When `user_narrative` contains a URL, the agent uses its web search tool to fetch that
page and fold the content into the prompt.

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
    "sound_profile": "upbeat_pop",
    "finetune_id": "gduoyhnzn5nvb246gg7i",
    "delivery_and_control": "balanced_studio",
    "instrumental_only": false,
    "user_narrative": null
  }
}
```

The response includes an AI-generated `title` and `description` based on the generated prompt, making it easy to catalog and identify tracks. The `title` can be passed straight through to `/render` to name the saved file.

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
| `music_length_ms` | integer | No | see below | Total length in milliseconds (1000-300000) |

When `music_length_ms` is omitted, the service tries to extract a duration from the
prompt text and falls back to 30000 ms if it finds none.

**Response** (`music_v2` plan — a flat list of chunks):
```json
{
  "chunks": [
    {
      "text": "[Intro]",
      "positive_styles": ["120 BPM", "bright synthesizer hook", "uplifting electronic pop"],
      "negative_styles": [],
      "duration_ms": 6000,
      "context_adherence": "high"
    }
  ]
}
```

### POST /render

Render audio via the ElevenLabs `compose_detailed` API. Provide **either** `prompt`
**or** `chunks` — they are mutually exclusive and one is required.

**Request (composition-plan mode):**
```bash
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Bright Pop Anthem",
    "chunks": [
      {
        "text": "[Intro]",
        "positive_styles": ["120 BPM", "clean electric guitar riff"],
        "negative_styles": ["full band", "vocals"],
        "duration_ms": 6000,
        "context_adherence": "high"
      }
    ],
    "model_id": "music_v2"
  }'
```

**Request (prompt mode):**
```bash
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Quick Prompt Track",
    "prompt": "An upbeat 30-second bright pop-electro ad hook at 120 BPM in E major.",
    "music_length_ms": 30000,
    "force_instrumental": true,
    "output_format": "mp3_44100_128"
  }'
```

**Request Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | string | `null` | Text-to-music prompt. Mutually exclusive with `chunks` |
| `chunks` | array[Chunk] | `[]` | `music_v2` composition plan. Mutually exclusive with `prompt` |
| `music_length_ms` | integer | `null` | Song length (3000-600000). Prompt mode only |
| `model_id` | string | `"music_v2"` | `"music_v1"` or `"music_v2"` |
| `finetune_id` | string | `null` | ElevenLabs finetune to steer generation (see `GET /finetunes`) |
| `finetune_strength` | float | `null` | Finetune influence (0.0-1.0). Requires `finetune_id` |
| `force_instrumental` | boolean | `false` | Guarantee an instrumental result |
| `store_for_inpainting` | boolean | `false` | Store the song to allow later inpainting |
| `with_timestamps` | boolean | `false` | Return word-level timestamps |
| `sign_with_c2pa` | boolean | `false` | Sign with C2PA provenance metadata |
| `output_format` | string | `null` | e.g. `"mp3_44100_128"`, `"pcm_44100"`. Null lets the API choose |
| `title` | string | `null` | **Local only** — names the saved file, never sent to ElevenLabs |

**Chunk Object:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | No | Section marker and/or lyrics (e.g. `"[Intro]"`) |
| `positive_styles` | array[string] | No | Style descriptors for this chunk |
| `negative_styles` | array[string] | No | Styles to avoid in this chunk |
| `duration_ms` | integer | Yes | Duration in milliseconds |
| `context_adherence` | string | No | How strictly to follow surrounding context (e.g. `"high"`) |

Chunks accept extra fields, so newer `music_v2` keys (`conditioning_ref`,
`condition_strength`, …) pass through untouched.

**Response:**
```json
{
  "id": "01HXYZ...",
  "filename": "bright_pop_anthem.mp3",
  "file_path": "https://account.blob.core.windows.net/music/01HXYZ.mp3",
  "download_url": "/render/download/01HXYZ...",
  "stream_url": "/render/stream/01HXYZ...",
  "content_type": "audio/mpeg",
  "file_size_bytes": 524288,
  "duration_ms": 30000,
  "composition_plan": { ... },
  "song_metadata": { ... },
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-22T10:30:00"
}
```

Audio bytes go to the configured storage backend and the metadata row goes to the
database; `id` is the handle for retrieving it afterwards.

### WS /render/ws

Render with real-time progress updates. Same payload as `POST /render`, wrapped in a
message envelope.

```javascript
const ws = new WebSocket("ws://localhost:8000/render/ws");

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  // {"type": "progress", "stage": "generating", "progress_percent": 15, "message": "..."}
  // {"type": "result",   "data": { ...RenderResponse... }}
  // {"type": "error",    "error_code": "VALIDATION_ERROR", "message": "..."}
};

ws.onopen = () => ws.send(JSON.stringify({
  type: "render",
  composition_plan: { prompt: "An upbeat pop hook", music_length_ms: 30000 }
}));
```

Progress stages: `connected` (0%) → `validating` (5%) → `validated` (10%) →
`generating` (15%) → `processing` (70%) → `saving` (85%) → `extracting` (95%) →
`complete` (100%).

Error codes: `INVALID_REQUEST` (malformed message), `VALIDATION_ERROR` (bad
composition plan), `SERVER_ERROR` (render failure).

See [docs/frontend-websocket-integration.md](docs/frontend-websocket-integration.md) for a full client guide.

### GET /render/download/{identifier}

Download a previously rendered audio file. `identifier` is the render `id`; a filename
is also accepted for backward compatibility.

```bash
curl -O http://localhost:8000/render/download/01HXYZ...
```

### GET /render/stream/{identifier}

Stream a previously rendered audio file for playback (served inline with
`Accept-Ranges`).

```bash
curl http://localhost:8000/render/stream/01HXYZ...
```

### GET /finetunes

List ElevenLabs music finetunes so a frontend can build a picker without holding the
ElevenLabs API key. Pass the returned `id` as `finetune_id` on `/render`.

```bash
curl "http://localhost:8000/finetunes?model_id=music_v2&page_size=25"
```

**Query Parameters (all optional):**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_id` | string | - | Keep only finetunes for this model, e.g. `music_v2` |
| `visibility` | string | - | `private`, `workspace`, or `public` |
| `created_by` | string | - | `self`, `workspace`, or `elevenlabs` |
| `include_incomplete` | boolean | `false` | Include finetunes still training |
| `cursor` | string | - | Pagination cursor from a previous `next_cursor` |
| `page_size` | integer | - | Results per page (1-100) |
| `refresh` | boolean | `false` | Bypass the server cache and refetch |

**Response:**
```json
{
  "finetunes": [
    {
      "id": "ft_abc123",
      "name": "Synthwave Nights",
      "tags": ["synthwave", "retro"],
      "primary_genre": "electronic",
      "model_id": "music_v2",
      "status": "completed"
    }
  ],
  "count": 1,
  "has_more": false,
  "next_cursor": null
}
```

Results are cached in-memory for `FINETUNES_CACHE_TTL` seconds (default 300). See
[docs/FRONTEND_FINETUNES.md](docs/FRONTEND_FINETUNES.md).

### Available Presets

#### Project Blueprint (use case & structure)
- `ad_brand_fast_hook` - 30s ad/brand spot
- `podcast_voiceover_loop` - 60s loopable podcast bed
- `video_game_action_loop` - 90s loopable game music
- `meditation_sleep` - Ambient meditation/sleep
- `standalone_song_mini` - 90s mini-song (a target length stated in `user_narrative` overrides this)

#### Sound Profile (genre & sonic characteristics) — from a finetune, not a preset

There is no fixed genre list. `sound_profile` is a slug naming an ElevenLabs music finetune, and
`finetune_id` is that finetune's id — get both from [`GET /finetunes`](#get-finetunes). The backend resolves
the id to the finetune's real `name` / `primary_genre` / `tags`, and the agent derives tempo, key,
groove, harmony, instrumentation and vocal character from that metadata.

```jsonc
{ "sound_profile": "indie_dance", "finetune_id": "aslj0pdvdods2agammwb" }
```

- New finetunes work immediately — no code change here.
- `finetune_id` is **required**; omitting it returns `422` rather than defaulting the genre.
- If the finetune can't be resolved, the request still succeeds: a warning is logged and the genre is
  inferred from the slug.
- Send the same `finetune_id` to `/render` so the audio is generated in the style the prompt describes.

#### Delivery & Control (workflow preferences)
- `exploratory_iterate` - Exploratory with iteration
- `balanced_studio` - Balanced studio approach
- `blueprint_plan_first` - Blueprint planning first
- `live_one_take` - Live one-take recording
- `isolation_stems` - Isolated stem outputs

For detailed API documentation, see [docs/PROMPT_API.md](docs/PROMPT_API.md),
[docs/PLAN_API.md](docs/PLAN_API.md), and [docs/RENDER_API.md](docs/RENDER_API.md).

## Project Structure

```
.
├── main.py                 # FastAPI application entry point
├── config.py               # Centralized pydantic-settings configuration
├── models/                 # Pydantic models
│   ├── prompt.py          # Prompt request/response models + preset enums
│   ├── plan.py            # Composition plan / Chunk models
│   ├── render.py          # Render request/response models
│   ├── finetune.py        # Finetune listing models
│   └── websocket.py       # WebSocket progress/result/error messages
├── services/              # Business logic
│   ├── prompt_generator.py  # OpenAI Agents integration
│   ├── plan_generator.py    # ElevenLabs plan generation
│   ├── render_service.py    # ElevenLabs music rendering
│   ├── render_repository.py # Render metadata persistence
│   ├── finetune_service.py  # Finetune listing + in-memory cache
│   └── storage.py           # Local filesystem / Azure Blob backends
├── routers/               # API routes
│   ├── prompt.py          # /prompt
│   ├── plan.py            # /plan
│   ├── render.py          # /render, /render/ws, download, stream
│   └── finetunes.py       # /finetunes
├── db/                    # Async SQLAlchemy engine + ORM models
├── migrations/            # Alembic migrations
├── scripts/init_db.py     # Local database bootstrap
├── prompts/               # System prompt templates
│   └── generate_music_prompt.md
├── output/music/          # Rendered audio (local storage backend, runtime)
├── testing/               # Test scripts (see testing/README.md)
├── docs/                  # Per-endpoint API docs and integration guides
├── Dockerfile             # Container image
├── alembic.ini            # Alembic configuration
├── pyproject.toml         # Project dependencies
└── README.md              # This file
```

## Development

### Testing

Run the pipeline test scripts against a running server:

```bash
uv run python testing/test_prompt_endpoint.py
uv run python testing/test_plan_endpoint.py
uv run python testing/test_render_endpoint.py
uv run python testing/test_render_websocket.py
uv run python testing/test_finetunes_endpoint.py
uv run python testing/test_storage_and_db.py
```

See [testing/README.md](testing/README.md) for the full list, including the
experimental scripts.

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
# Required — validated at startup; the app refuses to boot without it
OPENAI_API_KEY=sk-...

# Required for /plan, /render, /finetunes — checked lazily on first service use
ELEVENLABS_API_KEY=...

# App (defaults shown)
APP_NAME=fastapi-starter
APP_VERSION=1.0.0
ENVIRONMENT=development

# OpenTelemetry
OTEL_ENABLED=true
OTEL_EXPORTER_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=fastapi-app

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://localhost:8000"]

# Rendered-music storage: "local" or "azure"
STORAGE_BACKEND=local
LOCAL_STORAGE_DIR=output/music
# Azure Blob (required when STORAGE_BACKEND=azure — one of these two)
AZURE_STORAGE_ACCOUNT_URL=https://<account>.blob.core.windows.net
AZURE_STORAGE_CONNECTION_STRING=
AZURE_STORAGE_CONTAINER=music
STORAGE_SIGNED_URLS=false

# Metadata database (async SQLAlchemy URL)
DATABASE_URL=sqlite+aiosqlite:///./data/renders.db
# Production: postgresql+asyncpg://user:pass@host/db

# Finetunes cache TTL in seconds (0 disables caching)
FINETUNES_CACHE_TTL=300
```

`STORAGE_BACKEND=azure` fails fast at startup unless `AZURE_STORAGE_ACCOUNT_URL`
(managed identity) or `AZURE_STORAGE_CONNECTION_STRING` is set.

## Architecture

### Three-Stage Pipeline

```
POST /prompt  →  POST /plan  →  POST /render (or WS /render/ws)
 presets to      prompt to        plan to audio + storage + metadata row
 prompt          composition plan
```

`/render` also accepts a plain `prompt` directly, so `/plan` can be skipped when you
don't need to inspect or edit the composition plan first.

### Request Flow

1. **Client** sends POST request to `/prompt` with preset selections
2. **Router** (`routers/prompt.py`) validates request with Pydantic
3. **Service** (`services/prompt_generator.py`) loads system prompt and creates agent
4. **Agent** (OpenAI Agents SDK, with `WebSearchTool`) returns structured output
5. **Router** returns formatted response with metadata

### Key Components

- **Models** (`models/`): Type-safe request/response schemas
- **Services** (`services/`): Agent management, ElevenLabs calls, storage, persistence
- **Routers** (`routers/`): HTTP/WebSocket handlers with observability
- **System Prompt** (`prompts/generate_music_prompt.md`): Expert music direction
  instructions — preset mappings and conflict-resolution rules for the agent

### Storage & Persistence

Rendered audio goes to a pluggable storage backend (`services/storage.py`): the local
filesystem in development, Azure Blob Storage in production (managed identity, or a
connection string for local testing). Render metadata — id, filename, blob key, size,
duration, composition plan — is written to the database via `services/render_repository.py`,
so `/render/download/{id}` and `/render/stream/{id}` can serve files across restarts and
across instances. Schema is managed by Alembic; in `development` the tables are also
created automatically at startup.

### Observability

The application includes comprehensive observability:

- **Tracing**: OpenTelemetry spans for all operations
- **Logging**: Structured JSON logs with request context
- **Metrics**: Request counters and error tracking
- **Request IDs**: Unique IDs for tracking requests end-to-end

## Deployment

### Docker

```bash
docker build -t elevenlabs-music-api .
docker run -p 8000:8000 --env-file .env elevenlabs-music-api
```

### Cloud Deployment

Azure Container Apps is the documented target — see
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the full runbook (Azure Blob storage,
Postgres, managed identity, migrations). The image also runs on AWS ECS/Fargate,
Google Cloud Run, or Kubernetes.

Health check endpoints:
- `/health` - Comprehensive health check (includes database connectivity)
- `/ready` - Readiness probe
- `/alive` - Liveness probe

## Further Documentation

| Document | Contents |
|----------|----------|
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | Fastest path to a running server |
| [docs/PROMPT_API.md](docs/PROMPT_API.md) | `/prompt` reference |
| [docs/PLAN_API.md](docs/PLAN_API.md) | `/plan` reference |
| [docs/RENDER_API.md](docs/RENDER_API.md) | `/render` reference |
| [docs/frontend-websocket-integration.md](docs/frontend-websocket-integration.md) | WebSocket client guide |
| [docs/FRONTEND_API_GUIDE.md](docs/FRONTEND_API_GUIDE.md) | Frontend integration overview |
| [docs/FRONTEND_FINETUNES.md](docs/FRONTEND_FINETUNES.md) | Building a finetune picker |
| [docs/FRONTEND_API_CHANGES_STORAGE.md](docs/FRONTEND_API_CHANGES_STORAGE.md) | Storage-related API changes |
| [docs/FRONTEND_DEPLOYED_BACKEND.md](docs/FRONTEND_DEPLOYED_BACKEND.md) | Talking to the deployed backend |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Azure Container Apps runbook |
| [docs/PRESETS_GUIDE.md](docs/PRESETS_GUIDE.md) | What each preset means |
| [docs/ADDING_PRESET_GUIDE.md](docs/ADDING_PRESET_GUIDE.md) | Adding a new preset |
| [docs/MIDDLEWARE.md](docs/MIDDLEWARE.md) | Middleware and request IDs |

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]
