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
COMP_PLAN_FILE = (
    Path(__file__).parent.parent
    / "prompts"
    / "comp_plan.json"
)
with open(COMP_PLAN_FILE, "r", encoding="utf-8") as f:
    COMP_PLAN = f.read()


#print(json.dumps(COMP_PLAN, indent=2))

track_details = elevenlabs.music.compose_detailed(
    composition_plan=json.loads(COMP_PLAN),
)

#print(track_details.json) # json contains composition_plan and song_metadata. The composition plan will include lyrics (if applicable)
print(json.dumps(track_details.json, indent=2))
print(track_details.filename)

# Save the audio to the music directory
music_dir = os.path.join(os.path.dirname(__file__), "music")
os.makedirs(music_dir, exist_ok=True)
output_path = os.path.join(music_dir, track_details.filename)
with open(output_path, "wb") as f:
    f.write(track_details.audio)
print(f"Saved to: {output_path}")

# track_details.audio contains the audio bytes from the downloaded file
#play(track_details.audio)
play(open(output_path, "rb").read())