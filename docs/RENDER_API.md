# Music Render API

This document covers the `/render` endpoint for rendering music from composition plans using the ElevenLabs API.

## Architecture

The implementation follows FastAPI best practices with a clean separation of concerns:

```
.
├── models/              # Pydantic models for request/response validation
│   ├── __init__.py
│   ├── render.py       # RenderRequest, RenderResponse
│   └── websocket.py    # WebSocket message types (ProgressMessage, etc.)
├── services/           # Business logic layer
│   ├── __init__.py
│   └── render_service.py  # ElevenLabs API integration
├── routers/            # API route handlers
│   ├── __init__.py
│   └── render.py       # /render endpoints (REST + WebSocket)
├── output/             # Generated audio files
│   └── music/          # MP3 files stored here
└── main.py             # FastAPI application entry point
```

## Endpoints Overview

| Endpoint | Method | Use Case |
|----------|--------|----------|
| `/render` | POST | Simple rendering without progress updates |
| `/render/ws` | WebSocket | Rendering with real-time progress updates |
| `/render/download/{filename}` | GET | Download audio file (attachment) |
| `/render/stream/{filename}` | GET | Stream audio file (inline playback) |

**When to use POST vs WebSocket:**
- Use `POST /render` for server-to-server calls, batch processing, or when you don't need progress feedback
- Use `WebSocket /render/ws` for user-facing applications where you want to show rendering progress

---

### POST /render

Renders music from a composition plan using the ElevenLabs `compose_detailed` API with the `music_v2` model.

#### Request Body

The endpoint renders from **either** a composition plan (`chunks`) **or** a text `prompt` —
the two are **mutually exclusive** (matching the ElevenLabs `compose_detailed` contract). All
other fields map directly to `compose_detailed` body parameters (with project defaults).

**Plan mode** — a flat list of `chunks`, each with its own positive/negative styles, duration,
optional lyrics/section marker (`text`), and context adherence:

```json
{
  "title": "Indie Sunrise",
  "chunks": [
    {
      "text": "[Intro]",
      "positive_styles": ["95 bpm", "indie pop", "clean electric guitar riff"],
      "negative_styles": ["full band", "vocals", "heavy reverb"],
      "duration_ms": 4000,
      "context_adherence": "high"
    },
    {
      "text": "[Verse 1]\nEmpty street starts to bloom,",
      "positive_styles": ["95 bpm", "warm male vocal", "steady bassline"],
      "negative_styles": ["shouting"],
      "duration_ms": 7000,
      "context_adherence": "high"
    }
  ]
}
```

**Prompt mode** — a text prompt plus optional length and pass-through params:

```json
{
  "title": "Quick Hook",
  "prompt": "An upbeat 30-second bright pop-electro ad hook at 120 BPM in E major.",
  "music_length_ms": 30000,
  "model_id": "music_v2",
  "force_instrumental": true,
  "output_format": "mp3_44100_128"
}
```

#### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | string \| null | one of prompt/chunks | `null` | Text-to-music prompt. **Mutually exclusive with `chunks`.** |
| `chunks` | array[Chunk] | one of prompt/chunks | `[]` | Composition plan sections. **Mutually exclusive with `prompt`.** |
| `music_length_ms` | integer \| null | No | `null` | **Only valid with `prompt`.** Range 3000–600000 (3–600 s). |
| `model_id` | string | No | `"music_v2"` | `"music_v1"` or `"music_v2"`. |
| `force_instrumental` | boolean | No | `false` | Guarantee an instrumental result. |
| `store_for_inpainting` | boolean | No | `false` | Store the song to allow later inpainting. |
| `with_timestamps` | boolean | No | `false` | Return word-level timestamps. |
| `sign_with_c2pa` | boolean | No | `false` | Sign the song with C2PA provenance. |
| `output_format` | string \| null | No | `null` (API default) | e.g. `"mp3_44100_128"`, `"pcm_44100"`. |
| `title` | string \| null | No | `null` | Local-only; names the output file. Not sent to ElevenLabs. |

> `seed` and `respect_sections_durations` from the REST API are intentionally **not** exposed —
> the pinned ElevenLabs SDK (2.58.0) does not support them.

#### Chunk Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | No | Section marker in square brackets (e.g. `[Intro]`) and/or lyric lines |
| `positive_styles` | array[string] | No | Styles to include in this chunk |
| `negative_styles` | array[string] | No | Styles to avoid in this chunk |
| `duration_ms` | integer | Yes | Duration in milliseconds (min: 3000) |
| `context_adherence` | string \| null | No | How strictly to adhere to surrounding chunks (e.g. `"high"`) |

#### Validation Rules (return `422`)

- Exactly one of `prompt` or `chunks` must be provided (not both, not neither).
- `music_length_ms` may only be supplied together with `prompt`.
- In plan mode, each chunk `duration_ms` must be ≥ 3000, and the total across chunks must be 3000–600000 ms.

#### Response

```json
{
  "filename": "track_abc123def456.mp3",
  "file_path": "D:/Projects/ElevenLabs-music/output/music/track_abc123def456.mp3",
  "download_url": "/render/download/track_abc123def456.mp3",
  "stream_url": "/render/stream/track_abc123def456.mp3",
  "content_type": "audio/mpeg",
  "file_size_bytes": 524288,
  "composition_plan": { ... },
  "song_metadata": { ... },
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-24T10:30:00Z"
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `filename` | string | Generated audio filename |
| `file_path` | string | Local path where the file is saved |
| `download_url` | string | URL to download the audio file |
| `stream_url` | string \| null | URL to stream the audio file for playback |
| `content_type` | string | MIME type (always "audio/mpeg") |
| `file_size_bytes` | integer | Size of the audio file in bytes |
| `composition_plan` | object \| null | Composition plan with any API modifications |
| `song_metadata` | object \| null | Metadata about the generated song |
| `request_id` | string | Unique request identifier |
| `timestamp` | string | ISO 8601 timestamp |

---

### GET /render/download/{filename}

Downloads a previously rendered audio file.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `filename` | string | The filename returned from POST /render |

#### Response

- **200 OK**: Returns the audio file with `Content-Type: audio/mpeg`
- **404 Not Found**: File does not exist

#### Headers

```
Content-Type: audio/mpeg
Content-Disposition: attachment; filename=track_abc123.mp3
Accept-Ranges: bytes
```

---

### GET /render/stream/{filename}

Streams a previously rendered audio file for in-browser playback.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `filename` | string | The filename returned from POST /render |

#### Response

- **200 OK**: Returns the audio stream with `Content-Type: audio/mpeg`
- **404 Not Found**: File does not exist

#### Headers

```
Content-Type: audio/mpeg
Content-Length: 524288
Content-Disposition: inline; filename=track_abc123.mp3
Accept-Ranges: bytes
```

---

### WebSocket /render/ws

Renders music with real-time progress updates. Use this instead of `POST /render` when you want to show progress to users during the rendering process.

#### Connection URL

```
ws://localhost:8000/render/ws
```

#### Protocol Flow

```
Client                                    Server
   |                                         |
   |--------- WebSocket Connect ------------>|
   |                                         |
   |<-- {"type":"progress","stage":"connected","progress_percent":0,...}
   |                                         |
   |-- {"type":"render","composition_plan":{...}} -->
   |                                         |
   |<-- {"type":"progress","stage":"validating","progress_percent":5,...}
   |<-- {"type":"progress","stage":"validated","progress_percent":10,...}
   |<-- {"type":"progress","stage":"generating","progress_percent":15,...}
   |                                         |
   |            (ElevenLabs API call)        |
   |      Progress updates every 2 seconds   |
   |                                         |
   |<-- {"type":"progress","stage":"generating","progress_percent":20,...}
   |<-- {"type":"progress","stage":"generating","progress_percent":25,...}
   |<-- ...                                  |
   |<-- {"type":"progress","stage":"generating","progress_percent":65,...}
   |                                         |
   |            (API call completes)         |
   |      Progress updates every 0.5 seconds |
   |                                         |
   |<-- {"type":"progress","stage":"processing","progress_percent":70,...}
   |<-- {"type":"progress","stage":"processing","progress_percent":75,...}
   |<-- {"type":"progress","stage":"saving","progress_percent":80,...}
   |<-- ...                                  |
   |<-- {"type":"progress","stage":"extracting","progress_percent":95,...}
   |<-- {"type":"progress","stage":"complete","progress_percent":100,...}
   |                                         |
   |<-- {"type":"result","data":{...}}       |
   |                                         |
   |<-------- Connection Closed -------------|
```

#### Client Request Message

After connecting, send a single JSON message to start rendering:

```json
{
  "type": "render",
  "composition_plan": {
    "title": "My Song Title",
    "chunks": [
      {
        "text": "[Intro]",
        "positive_styles": ["ambient", "relaxing", "soft piano", "soft pads", "gentle melody"],
        "negative_styles": ["aggressive", "loud", "drums", "bass"],
        "duration_ms": 5000,
        "context_adherence": "high"
      }
    ]
  }
}
```

#### Request Fields

The `composition_plan` field carries a **full render request** (the same body as `POST /render`,
see [Request Fields](#request-fields) above), so it supports **both** plan mode (`chunks`) and
prompt mode (`prompt` + `music_length_ms`) plus all pass-through params (`model_id`,
`force_instrumental`, `output_format`, etc.).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"render"` | Yes | Must be exactly `"render"` |
| `composition_plan` | RenderRequest | Yes | Full render request — provide **either** `chunks` **or** `prompt` (mutually exclusive) |

> The field name is `composition_plan` for historical reasons, but it accepts the entire render
> request, including prompt-mode fields. Example (prompt mode):
> ```json
> { "type": "render", "composition_plan": { "title": "Quick Hook", "prompt": "An upbeat 30-second hook", "music_length_ms": 30000 } }
> ```

#### Validation Rules

- Provide exactly one of `prompt` or `chunks` (not both, not neither).
- `music_length_ms` only with `prompt` (range 3,000–600,000 ms).
- Plan mode: total duration 3,000–600,000 ms (3 s–10 min); each chunk ≥ 3,000 ms.

#### Server Messages

**1. Progress Message**

Sent multiple times during rendering to update progress:

```json
{
  "type": "progress",
  "stage": "generating",
  "progress_percent": 15,
  "message": "Starting music generation with ElevenLabs API...",
  "timestamp": "2024-01-26T12:00:00.000000"
}
```

**Progress Stages (in order):**

| Stage | Percent Range | Interval | Description |
|-------|---------------|----------|-------------|
| `connected` | 0% | instant | Connection established, waiting for request |
| `validating` | 5% | instant | Validating composition plan structure |
| `validated` | 10% | instant | Validation complete |
| `generating` | 15% → 65% | 2 seconds | ElevenLabs API call in progress (simulated progress) |
| `processing` | 70% → 75% | 0.5 seconds | Processing API response |
| `saving` | 80% → 90% | 0.5 seconds | Saving audio file to disk |
| `extracting` | 95% | 0.5 seconds | Extracting metadata |
| `complete` | 100% | instant | Render complete |

**Smooth Progress Behavior:**

The WebSocket endpoint provides smooth, gradual progress updates throughout the entire rendering process:

1. **Validation phase (0% → 15%)**: Instant updates for quick validation steps
2. **Generation phase (15% → 65%)**: Simulated progress updates every **2 seconds** while waiting for the ElevenLabs API. Since the API doesn't provide streaming progress, updates are simulated to keep the UI responsive.
3. **Post-processing phase (65% → 100%)**: Gradual updates every **0.5 seconds** through processing, saving, and metadata extraction stages.

This ensures users see continuous progress feedback rather than long periods of no updates followed by sudden jumps.

**2. Result Message (on success)**

Sent once when rendering completes successfully:

```json
{
  "type": "result",
  "data": {
    "filename": "my_song_title_a1b2c3d4.mp3",
    "file_path": "D:\\Projects\\ElevenLabs-music\\output\\music\\my_song_title_a1b2c3d4.mp3",
    "download_url": "/render/download/my_song_title_a1b2c3d4.mp3",
    "stream_url": "/render/stream/my_song_title_a1b2c3d4.mp3",
    "content_type": "audio/mpeg",
    "file_size_bytes": 524288,
    "composition_plan": { ... },
    "song_metadata": { ... },
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-26T12:00:05.000000"
  }
}
```

**3. Error Message (on failure)**

Sent when an error occurs:

```json
{
  "type": "error",
  "error_code": "VALIDATION_ERROR",
  "message": "Composition plan must have at least one chunk.",
  "timestamp": "2024-01-26T12:00:00.000000"
}
```

**Error Codes:**

| Code | Cause |
|------|-------|
| `INVALID_REQUEST` | Message wasn't valid JSON, or the envelope is malformed (e.g. wrong/missing `type`) |
| `VALIDATION_ERROR` | The render request failed validation (empty, both `prompt` and `chunks`, `music_length_ms` without a prompt, or a chunk duration too short/long) |
| `SERVER_ERROR` | ElevenLabs API failure or unexpected server error |

#### JavaScript/TypeScript Example

```typescript
function renderWithProgress(
  compositionPlan: object,
  onProgress: (stage: string, percent: number, message: string) => void
): Promise<object> {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket("ws://localhost:8000/render/ws");

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      switch (message.type) {
        case "progress":
          onProgress(message.stage, message.progress_percent, message.message);

          // Send composition plan after receiving "connected"
          if (message.stage === "connected") {
            ws.send(JSON.stringify({
              type: "render",
              composition_plan: compositionPlan,
            }));
          }
          break;

        case "result":
          resolve(message.data);
          ws.close();
          break;

        case "error":
          reject(new Error(`${message.error_code}: ${message.message}`));
          ws.close();
          break;
      }
    };

    ws.onerror = () => reject(new Error("WebSocket connection failed"));
  });
}

// Usage
renderWithProgress(
  {
    title: "My Song",
    chunks: [{ text: "[Intro]", positive_styles: ["ambient"], negative_styles: [], duration_ms: 5000, context_adherence: "high" }]
  },
  (stage, percent, message) => {
    console.log(`[${percent}%] ${stage}: ${message}`);
    // Update your progress bar here
  }
).then(result => {
  console.log("Audio URL:", result.stream_url);
});
```

#### Python Example

```python
import asyncio
import json
import websockets

async def render_with_progress(composition_plan, on_progress):
    uri = "ws://localhost:8000/render/ws"

    async with websockets.connect(uri) as ws:
        while True:
            msg = json.loads(await ws.recv())

            if msg["type"] == "progress":
                on_progress(msg["stage"], msg["progress_percent"], msg["message"])

                if msg["stage"] == "connected":
                    await ws.send(json.dumps({
                        "type": "render",
                        "composition_plan": composition_plan
                    }))

            elif msg["type"] == "result":
                return msg["data"]

            elif msg["type"] == "error":
                raise Exception(f"{msg['error_code']}: {msg['message']}")

# Usage
result = asyncio.run(render_with_progress(
    {
        "title": "My Song",
        "chunks": [{"text": "[Intro]", "positive_styles": ["ambient"], "duration_ms": 5000, "context_adherence": "high"}]
    },
    lambda stage, pct, msg: print(f"[{pct}%] {stage}: {msg}")
))
print(f"Audio URL: {result['stream_url']}")
```

---

## Example Usage

### Complete Workflow with cURL

```bash
# Step 1: Render music from composition plan
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{
    "chunks": [
      {
        "text": "[Intro]",
        "positive_styles": ["95 bpm", "indie pop", "uplifting", "clean guitar", "minimal"],
        "negative_styles": ["heavy reverb", "sad", "vocals"],
        "duration_ms": 4000,
        "context_adherence": "high"
      }
    ]
  }' > render_response.json

# Step 2: Extract filename and download
FILENAME=$(cat render_response.json | jq -r '.filename')
curl -O "http://localhost:8000/render/download/$FILENAME"
```

### Python Example

```python
import requests

# Render the music
composition_plan = {
    "chunks": [
        {
            "text": "[Intro]",
            "positive_styles": ["95 bpm", "indie pop", "uplifting", "clean guitar"],
            "negative_styles": ["heavy reverb", "sad", "vocals"],
            "duration_ms": 4000,
            "context_adherence": "high"
        },
        {
            "text": "[Verse]\nHello world, here we go",
            "positive_styles": ["95 bpm", "warm vocals"],
            "negative_styles": ["shouting"],
            "duration_ms": 8000,
            "context_adherence": "high"
        }
    ]
}

# POST to render
response = requests.post(
    "http://localhost:8000/render",
    json=composition_plan,
    timeout=300  # Rendering can take a while
)
result = response.json()

print(f"Generated: {result['filename']}")
print(f"Size: {result['file_size_bytes']} bytes")

# Download the audio
audio_response = requests.get(
    f"http://localhost:8000{result['download_url']}"
)
with open(result['filename'], 'wb') as f:
    f.write(audio_response.content)
```

### React/JavaScript Example

```javascript
async function renderAndPlayMusic(compositionPlan) {
  // Step 1: Render the music
  const renderResponse = await fetch('/render', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(compositionPlan)
  });
  
  const result = await renderResponse.json();
  console.log('Rendered:', result.filename);
  
  // Step 2: Play the audio using the stream endpoint
  const streamUrl = result.download_url.replace('/download/', '/stream/');
  const audio = new Audio(streamUrl);
  audio.play();
  
  return result;
}

// Usage
const plan = {
  chunks: [
    {
      text: '[Intro]',
      positive_styles: ['indie pop', 'uplifting', 'guitar'],
      negative_styles: ['sad'],
      duration_ms: 4000,
      context_adherence: 'high'
    }
  ]
};

renderAndPlayMusic(plan);
```

### React Component Example

```jsx
import React, { useState } from 'react';

function MusicPlayer({ compositionPlan }) {
  const [audioUrl, setAudioUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleRender = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(compositionPlan)
      });
      
      if (!response.ok) throw new Error('Render failed');
      
      const result = await response.json();
      const streamUrl = result.download_url.replace('/download/', '/stream/');
      setAudioUrl(streamUrl);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button onClick={handleRender} disabled={loading}>
        {loading ? 'Rendering...' : 'Generate Music'}
      </button>
      
      {error && <p className="error">{error}</p>}
      
      {audioUrl && (
        <audio controls src={audioUrl}>
          Your browser does not support the audio element.
        </audio>
      )}
    </div>
  );
}
```

---

## Error Responses

### 422 Validation Error

```json
{
  "detail": [
    {
      "loc": ["body", "chunks", 0, "duration_ms"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 404 Not Found (for download/stream)

```json
{
  "detail": "Audio file not found: nonexistent_file.mp3"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Music rendering failed: API error message here"
}
```

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ELEVENLABS_API_KEY` | Yes | Your ElevenLabs API key |

### Output Directory

Rendered audio files are saved to:
```
project_root/output/music/
```

The directory is created automatically if it doesn't exist.

---

## Testing

### REST Endpoints

Run the test script to verify REST render endpoints:

```bash
uv run python testing/test_render_endpoint.py
```

This tests:
- POST /render with a sample composition plan
- GET /render/download/{filename}
- GET /render/stream/{filename}
- 404 handling for non-existent files

### WebSocket Endpoint

Run the WebSocket test script:

```bash
# Install websockets library first
pip install websockets

# Run the test
python testing/test_render_websocket.py
```

This tests:
- WebSocket connection to /render/ws
- Progress message flow
- Final result message
- Validation error handling

---

## Performance Notes

- **Timeout**: Rendering can take 30-120 seconds depending on composition complexity
- **File Size**: Typical MP3 files are 500KB-2MB for 30-second tracks
- **Format**: Output is always MP3 at 44.1kHz, 128kbps

---

## Related Documentation

- [Plan API](./PLAN_API.md) - Generate composition plans from text prompts
- [Prompt API](./PROMPT_API.md) - Generate music prompts
- [Quick Start](./QUICKSTART.md) - Getting started guide
