# Quick Start Guide

Get the music generation API up and running in 5 minutes!

## Prerequisites

- Python 3.12+
- OpenAI API key
- ElevenLabs API key

## Step 1: Set Up Environment

```bash
# Create .env file with your API keys
echo "OPENAI_API_KEY=sk-your-key-here" > .env
echo "ELEVENLABS_API_KEY=your-elevenlabs-key" >> .env
```

## Step 2: Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

## Step 3: Start the Server

```bash
uv run python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 4: Test the Endpoints

### Option A: Use the Interactive Docs

1. Open http://localhost:8000/docs in your browser
2. Explore the available endpoints:
   - `POST /prompt` - Generate music prompts
   - `POST /plan` - Generate composition plans
   - `POST /render` - Render music from composition plans
3. Click "Try it out" on any endpoint

### Option B: Use cURL

**Generate a music prompt:**
```bash
curl -X POST http://localhost:8000/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "project_blueprint": "ad_brand_fast_hook",
    "sound_profile": "bright_pop_electro",
    "delivery_and_control": "balanced_studio"
  }'
```

**Generate a composition plan:**
```bash
curl -X POST http://localhost:8000/plan \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create an uplifting indie pop track",
    "music_length_ms": 30000
  }'
```

**Render music from a plan:**
```bash
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{
    "positive_global_styles": ["indie pop", "uplifting"],
    "negative_global_styles": ["sad"],
    "sections": [
      {
        "section_name": "Intro",
        "positive_local_styles": ["guitar"],
        "negative_local_styles": [],
        "duration_ms": 4000,
        "lines": []
      }
    ]
  }'
```

### Option C: Run the Test Scripts

```bash
# Test prompt endpoint
uv run python testing/test_prompt_endpoint.py

# Test plan endpoint
uv run python testing/test_plan_endpoint.py

# Test render endpoint
uv run python testing/test_render_endpoint.py
```

### Option D: Run Usage Examples

```bash
uv run python examples/usage_examples.py
```

## What You'll Get

A response like:

```json
{
  "prompt": "Create a calming, meditative track that...",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-22T10:30:00Z",
  "input_parameters": {
    "project_blueprint": "meditation_sleep",
    "sound_profile": "lofi_cozy",
    "delivery_and_control": "exploratory_iterate",
    "instrumental_only": true
  }
}
```

The `prompt` field contains the generated music prompt ready to use with ElevenLabs music-1 model!

## Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/prompt` | POST | Generate music prompts from presets |
| `/plan` | POST | Generate composition plans from text |
| `/render` | POST | Render music from composition plans |
| `/render/download/{filename}` | GET | Download rendered audio |
| `/render/stream/{filename}` | GET | Stream rendered audio |

## Complete Workflow Example

```python
import requests

# Step 1: Generate a composition plan
plan_response = requests.post(
    "http://localhost:8000/plan",
    json={
        "prompt": "Create an uplifting indie pop track",
        "music_length_ms": 20000
    }
)
composition_plan = plan_response.json()

# Step 2: Render the music
render_response = requests.post(
    "http://localhost:8000/render",
    json=composition_plan,
    timeout=300
)
result = render_response.json()

# Step 3: Download the audio
audio = requests.get(f"http://localhost:8000{result['download_url']}")
with open(result['filename'], 'wb') as f:
    f.write(audio.content)

print(f"Saved: {result['filename']}")
```

## Available Presets

### Project Blueprint (What you're creating)
- `ad_brand_fast_hook` - 30-second ad/brand spot
- `podcast_voiceover_loop` - Podcast background music
- `video_game_action_loop` - Video game music loop
- `meditation_sleep` - Meditation/wellness track
- `standalone_song_mini` - Mini-song (90 seconds)

### Sound Profile (How it sounds)
- `bright_pop_electro` - Uplifting electronic
- `dark_trap_night` - Dark trap/hip-hop
- `lofi_cozy` - Cozy lo-fi beats
- `epic_cinematic` - Epic orchestral
- `indie_live_band` - Indie live band

### Delivery & Control (How it's made)
- `exploratory_iterate` - Exploratory approach
- `balanced_studio` - Balanced production
- `blueprint_plan_first` - Plan before execution
- `live_one_take` - Live recording feel
- `isolation_stems` - Isolated tracks

## Troubleshooting

### "Connection refused"
Make sure the server is running with `uv run python main.py`

### "OpenAI API key not found"
Check that `.env` file exists with `OPENAI_API_KEY=sk-...`

### "ElevenLabs API key not found"
Check that `.env` file contains `ELEVENLABS_API_KEY=...`

### "Module not found"
Run `uv sync` to install dependencies

### Render timeout
Rendering can take 30-120 seconds. Increase your client timeout.

### Still having issues?
Check the detailed documentation:
- [README.md](../README.md) - Full documentation
- [PROMPT_API.md](PROMPT_API.md) - Prompt endpoint details
- [PLAN_API.md](PLAN_API.md) - Plan endpoint details
- [RENDER_API.md](RENDER_API.md) - Render endpoint details
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Technical details

## Next Steps

1. Explore the interactive docs: http://localhost:8000/docs
2. Try different preset combinations
3. Generate composition plans from text prompts
4. Render and download music
5. Build your application!

## Need Help?

- Check examples: `examples/usage_examples.py`
- Run tests: `testing/test_*.py`
- Read API docs: http://localhost:8000/docs
- Review code: Start with `routers/`

Happy music generating! 🎵
