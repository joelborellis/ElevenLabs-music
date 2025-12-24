# Composition Plan API

This document covers the `/plan` endpoint for generating structured composition plans for the ElevenLabs music API.

## Architecture

The implementation follows FastAPI best practices with a clean separation of concerns:

```
.
├── models/              # Pydantic models for request/response validation
│   ├── __init__.py
│   └── plan.py         # PlanGenerationRequest, CompositionPlanResponse, Section
├── services/           # Business logic layer
│   ├── __init__.py
│   └── plan_generator.py  # OpenAI Agents integration for plan generation
├── routers/            # API route handlers
│   ├── __init__.py
│   └── plan.py         # /plan endpoint
└── main.py             # FastAPI application entry point
```

## Endpoint: POST /plan

Generates a structured composition plan based on a text prompt. The composition plan can be used directly with the ElevenLabs `compose_detailed` API or the `/render` endpoint.

### Request Body

```json
{
  "prompt": "Create an uplifting electronic pop track with a catchy hook",
  "music_length_ms": 30000
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | Text description of the desired music composition |
| `music_length_ms` | integer | No | 30000 | Total length of the music in milliseconds (1000-300000) |

### Response

```json
{
  "positive_global_styles": [
    "electronic pop",
    "high-energy",
    "uplifting",
    "122 bpm",
    "E major"
  ],
  "negative_global_styles": [
    "dark",
    "slow tempo",
    "acoustic"
  ],
  "sections": [
    {
      "section_name": "Intro",
      "positive_local_styles": [
        "bright synth chords",
        "punchy drums"
      ],
      "negative_local_styles": [
        "vocals",
        "slow build-up"
      ],
      "duration_ms": 4000,
      "lines": [],
      "source_from": null
    },
    {
      "section_name": "Verse 1",
      "positive_local_styles": [
        "catchy melody",
        "rhythmic bassline"
      ],
      "negative_local_styles": [
        "heavy distortion"
      ],
      "duration_ms": 8000,
      "lines": [
        "Feel the rhythm in the night,",
        "Everything is gonna be alright."
      ],
      "source_from": null
    }
  ]
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `positive_global_styles` | array[string] | Style descriptors to include throughout the composition |
| `negative_global_styles` | array[string] | Style descriptors to avoid throughout the composition |
| `sections` | array[Section] | List of sections making up the composition |

#### Section Fields

| Field | Type | Description |
|-------|------|-------------|
| `section_name` | string | Name of the section (e.g., "Intro", "Verse 1", "Chorus") |
| `positive_local_styles` | array[string] | Style descriptors to include in this section |
| `negative_local_styles` | array[string] | Style descriptors to avoid in this section |
| `duration_ms` | integer | Duration of this section in milliseconds |
| `lines` | array[string] | Lyric lines for this section (empty for instrumental) |
| `source_from` | string | null | Source reference for this section |

### Example Usage

#### Using cURL

```bash
curl -X POST http://localhost:8000/plan \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a dark ambient soundscape for a horror game with building tension",
    "music_length_ms": 60000
  }'
```

#### Using Python

```python
import requests

response = requests.post(
    "http://localhost:8000/plan",
    json={
        "prompt": "Create an uplifting indie pop track with heartfelt vocals",
        "music_length_ms": 30000
    }
)

composition_plan = response.json()
print(composition_plan)
```

#### Using JavaScript/Fetch

```javascript
const response = await fetch('http://localhost:8000/plan', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    prompt: 'Create a lo-fi hip hop beat for studying',
    music_length_ms: 45000
  })
});

const compositionPlan = await response.json();
console.log(compositionPlan);
```

### Error Responses

#### 422 Validation Error

```json
{
  "detail": [
    {
      "loc": ["body", "prompt"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### 500 Internal Server Error

```json
{
  "error": "Internal Server Error",
  "message": "An unexpected error occurred. Please contact support with the request ID.",
  "request_id": "uuid-here",
  "timestamp": "2025-12-24T10:30:00Z"
}
```

## Integration with /render Endpoint

The composition plan output from `/plan` can be directly passed to the `/render` endpoint to generate audio:

```python
import requests

# Step 1: Generate composition plan
plan_response = requests.post(
    "http://localhost:8000/plan",
    json={
        "prompt": "Create an uplifting indie pop track",
        "music_length_ms": 30000
    }
)
composition_plan = plan_response.json()

# Step 2: Render the music
render_response = requests.post(
    "http://localhost:8000/render",
    json=composition_plan
)
render_result = render_response.json()

# Step 3: Download or stream the audio
audio_url = f"http://localhost:8000{render_result['download_url']}"
```

## Testing

Run the test script to verify the endpoint is working:

```bash
uv run python testing/test_plan_endpoint.py
```

## Related Documentation

- [Render API](./RENDER_API.md) - Render music from composition plans
- [Prompt API](./PROMPT_API.md) - Generate music prompts
- [Quick Start](./QUICKSTART.md) - Getting started guide
