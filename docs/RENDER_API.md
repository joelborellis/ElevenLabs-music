# Music Render API

This document covers the `/render` endpoint for rendering music from composition plans using the ElevenLabs API.

## Architecture

The implementation follows FastAPI best practices with a clean separation of concerns:

```
.
├── models/              # Pydantic models for request/response validation
│   ├── __init__.py
│   └── render.py       # RenderRequest, RenderResponse
├── services/           # Business logic layer
│   ├── __init__.py
│   └── render_service.py  # ElevenLabs API integration
├── routers/            # API route handlers
│   ├── __init__.py
│   └── render.py       # /render endpoints
├── output/             # Generated audio files
│   └── music/          # MP3 files stored here
└── main.py             # FastAPI application entry point
```

## Endpoints

### POST /render

Renders music from a composition plan using the ElevenLabs `compose_detailed` API.

#### Request Body

```json
{
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
      "source_from": null
    },
    {
      "section_name": "Verse 1",
      "positive_local_styles": [
        "warm male vocal",
        "steady bassline"
      ],
      "negative_local_styles": [
        "shouting"
      ],
      "duration_ms": 7000,
      "lines": [
        "Empty street starts to bloom,",
        "chasing shadows from the room."
      ],
      "source_from": null
    }
  ]
}
```

#### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `positive_global_styles` | array[string] | No | Style descriptors to include globally |
| `negative_global_styles` | array[string] | No | Style descriptors to avoid globally |
| `sections` | array[Section] | No | List of sections in the composition |

#### Section Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `section_name` | string | Yes | Name of the section |
| `positive_local_styles` | array[string] | No | Styles to include in this section |
| `negative_local_styles` | array[string] | No | Styles to avoid in this section |
| `duration_ms` | integer | Yes | Duration in milliseconds |
| `lines` | array[string] | No | Lyric lines for this section |
| `source_from` | string | null | No | Source reference |

#### Response

```json
{
  "filename": "track_abc123def456.mp3",
  "file_path": "D:/Projects/ElevenLabs-music/output/music/track_abc123def456.mp3",
  "download_url": "/render/download/track_abc123def456.mp3",
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
| `content_type` | string | MIME type (always "audio/mpeg") |
| `file_size_bytes` | integer | Size of the audio file in bytes |
| `composition_plan` | object | null | Composition plan with any API modifications |
| `song_metadata` | object | null | Metadata about the generated song |
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

## Example Usage

### Complete Workflow with cURL

```bash
# Step 1: Render music from composition plan
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{
    "positive_global_styles": ["indie pop", "uplifting", "95 bpm"],
    "negative_global_styles": ["heavy reverb", "sad"],
    "sections": [
      {
        "section_name": "Intro",
        "positive_local_styles": ["clean guitar", "minimal"],
        "negative_local_styles": ["vocals"],
        "duration_ms": 4000,
        "lines": []
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
    "positive_global_styles": ["indie pop", "uplifting", "95 bpm"],
    "negative_global_styles": ["heavy reverb", "sad"],
    "sections": [
        {
            "section_name": "Intro",
            "positive_local_styles": ["clean guitar"],
            "negative_local_styles": ["vocals"],
            "duration_ms": 4000,
            "lines": [],
            "source_from": None
        },
        {
            "section_name": "Verse",
            "positive_local_styles": ["warm vocals"],
            "negative_local_styles": ["shouting"],
            "duration_ms": 8000,
            "lines": ["Hello world, here we go"],
            "source_from": None
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
  positive_global_styles: ['indie pop', 'uplifting'],
  negative_global_styles: ['sad'],
  sections: [
    {
      section_name: 'Intro',
      positive_local_styles: ['guitar'],
      negative_local_styles: [],
      duration_ms: 4000,
      lines: [],
      source_from: null
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
      "loc": ["body", "sections", 0, "duration_ms"],
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

Run the test script to verify all render endpoints:

```bash
uv run python testing/test_render_endpoint.py
```

This tests:
- POST /render with a sample composition plan
- GET /render/download/{filename}
- GET /render/stream/{filename}
- 404 handling for non-existent files

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
