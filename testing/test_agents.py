import asyncio
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv

from pydantic import BaseModel
from agents import Agent, Runner, trace

# Load environment variables from .env file
load_dotenv()

"""
CLI wizard that collects 3 preset selections (+ instrumental_only override),
then calls the Prompt Architect agent to generate a single downstream prompt.
"""

# Load the instructions from the system prompt file
PROMPT_INSTRUCTIONS_PATH = (
    Path(__file__).parent.parent
    / "prompts"
    / "system_prompt_eleven_music_3choice_wizard_prompt_architect_NEW.md"
)
with open(PROMPT_INSTRUCTIONS_PATH, "r", encoding="utf-8") as f:
    PROMPT_GENERATOR_INSTRUCTIONS = f.read()


# --- Stable IDs for the 3-choice wizard ---
class ProjectBlueprint(str, Enum):
    AD_BRAND_FAST_HOOK = "ad_brand_fast_hook"
    PODCAST_VOICEOVER_LOOP = "podcast_voiceover_loop"
    VIDEO_GAME_ACTION_LOOP = "video_game_action_loop"
    MEDITATION_SLEEP = "meditation_sleep"
    STANDALONE_SONG_MINI = "standalone_song_mini"


class SoundProfile(str, Enum):
    BRIGHT_POP_ELECTRO = "bright_pop_electro"
    DARK_TRAP_NIGHT = "dark_trap_night"
    LOFI_COZY = "lofi_cozy"
    EPIC_CINEMATIC = "epic_cinematic"
    INDIE_LIVE_BAND = "indie_live_band"


class DeliveryAndControl(str, Enum):
    EXPLORATORY_ITERATE = "exploratory_iterate"
    BALANCED_STUDIO = "balanced_studio"
    BLUEPRINT_PLAN_FIRST = "blueprint_plan_first"
    LIVE_ONE_TAKE = "live_one_take"
    ISOLATION_STEMS = "isolation_stems"


# --- The input schema your agent will receive ---
class WizardSelectionInput(BaseModel):
    project_blueprint: ProjectBlueprint
    sound_profile: SoundProfile
    delivery_and_control: DeliveryAndControl
    instrumental_only: bool = False


# IMPORTANT: In the Agents SDK, the input model should be passed via `output_type=...`
# (not `prompt=...`). This makes `final_output` parse/validate into your model type.
prompt_generator_agent = Agent(
    name="prompt_generator_agent",
    instructions=PROMPT_GENERATOR_INSTRUCTIONS,
    output_type=str,  # your agent's final output is a markdown prompt (string)
)


# --- Simple CLI helpers ---
def _pick_from_enum(title: str, enum_cls: type[Enum]) -> str:
    items = list(enum_cls)
    print(f"\n{title}")
    for i, item in enumerate(items, start=1):
        print(f"  {i}. {item.value}")

    while True:
        raw = input("Choose a number: ").strip()
        try:
            idx = int(raw)
            if 1 <= idx <= len(items):
                return items[idx - 1].value
        except ValueError:
            pass
        print(f"Invalid choice. Enter a number 1–{len(items)}.")


def _prompt_bool(question: str, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{question} ({suffix}): ").strip().lower()
        if raw == "":
            return default
        if raw in {"y", "yes", "true", "t", "1"}:
            return True
        if raw in {"n", "no", "false", "f", "0"}:
            return False
        print("Please enter y or n.")


async def main():
    print("=== Eleven Music 3-Choice Wizard ===")

    project_blueprint = _pick_from_enum("Project Blueprint", ProjectBlueprint)
    sound_profile = _pick_from_enum("Sound Profile", SoundProfile)
    delivery_and_control = _pick_from_enum("Delivery & Control", DeliveryAndControl)
    instrumental_only = _prompt_bool("Instrumental only override?", default=False)

    # Build a validated payload (IDs)
    wizard_input = WizardSelectionInput(
        project_blueprint=project_blueprint,
        sound_profile=sound_profile,
        delivery_and_control=delivery_and_control,
        instrumental_only=False,
    )

    # The agent expects the three keys: project_blueprint, sound_profile, delivery_and_control.
    # We'll pass the validated payload as JSON-ish text so the agent can parse it robustly.
    # (Your system prompt already supports JSON/YAML/key:value/bullets.)
    user_message = wizard_input.model_dump_json(indent=2)

    print(user_message)

    with trace("Deterministic Eleven Music flow"):
        prompt_result = await Runner.run(
            prompt_generator_agent,
            user_message,
        )

    print("\n=== Generated Downstream Prompt ===\n")
    print(prompt_result.final_output)


if __name__ == "__main__":
    asyncio.run(main())