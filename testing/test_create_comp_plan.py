from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
from pathlib import Path
import os
import json
from dotenv import load_dotenv
load_dotenv()

elevenlabs = ElevenLabs(
api_key=os.getenv("ELEVENLABS_API_KEY"),
)

# Load the instructions from the system prompt file
PROMPT = (
    Path(__file__).parent.parent
    / "prompts"
    / "user_prompt.txt"
)
with open(PROMPT, "r", encoding="utf-8") as f:
    USER_PROMPT = f.read()

composition_plan = elevenlabs.music.composition_plan.create(
    prompt=USER_PROMPT,
    music_length_ms=10000,
)

print(json.dumps(composition_plan.model_dump(), indent=2))