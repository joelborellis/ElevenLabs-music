# Quick Start Guide

Get the `/prompt` endpoint up and running in 5 minutes!

## Prerequisites

- Python 3.12+
- OpenAI API key

## Step 1: Set Up Environment

```bash
# Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=sk-your-key-here" > .env
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

## Step 4: Test the Endpoint

### Option A: Use the Interactive Docs

1. Open http://localhost:8000/docs in your browser
2. Click on `POST /prompt`
3. Click "Try it out"
4. Use the example request:
   ```json
   {
     "project_blueprint": "ad_brand_fast_hook",
     "sound_profile": "bright_pop_electro",
     "delivery_and_control": "balanced_studio",
     "instrumental_only": false
   }
   ```
5. Click "Execute"

### Option B: Use cURL

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

### Option C: Run the Test Script

```bash
uv run python testing/test_prompt_endpoint.py
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

### "Module not found"
Run `uv sync` to install dependencies

### Still having issues?
Check the detailed documentation:
- [README.md](../README.md) - Full documentation
- [PROMPT_API.md](PROMPT_API.md) - API details
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Technical details

## Next Steps

1. Explore the interactive docs: http://localhost:8000/docs
2. Try different preset combinations
3. Review the generated prompts
4. Integrate with ElevenLabs API
5. Build your application!

## Need Help?

- Check examples: `examples/usage_examples.py`
- Run tests: `testing/test_prompt_endpoint.py`
- Read API docs: http://localhost:8000/docs
- Review code: Start with `routers/prompt.py`

Happy music generating! 🎵
