"""
Simple test script to verify the /prompt endpoint works.

This script demonstrates how to use the /prompt endpoint programmatically.
"""

import asyncio
import json
import re
import httpx
from pathlib import Path
from pprint import pprint


# Test payloads live in this JSON file so variations can be changed without
# editing the script. It contains a "default" payload (used for the single
# request) and a "cases" list (used by --all).
TEST_CASES_PATH = Path(__file__).parent / "prompt_test_cases.json"

# The generated prompt is written here as a ready-to-use /plan request body so it
# can flow straight into test_plan_endpoint.py (which prefers this file when present).
GENERATED_PROMPT_PATH = Path(__file__).parent / "generated_prompt.json"

# Default song length (ms) used when no duration can be parsed from the prompt.
DEFAULT_MUSIC_LENGTH_MS = 30000


def load_test_data() -> dict:
    """Load the default payload and preset combinations from the JSON file."""
    with open(TEST_CASES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_music_length_ms(prompt: str) -> int:
    """Best-effort duration parse from prompt text (mirrors the /plan service).

    Looks for "N second(s)" or "N minute(s)"; falls back to the default length.
    """
    seconds = re.search(r"(\d+(?:\.\d+)?)\s*[-\s]?\s*seconds?", prompt, re.IGNORECASE)
    if seconds:
        return int(float(seconds.group(1)) * 1000)
    minutes = re.search(r"(\d+(?:\.\d+)?)\s*[-\s]?\s*minutes?", prompt, re.IGNORECASE)
    if minutes:
        return int(float(minutes.group(1)) * 60 * 1000)
    return DEFAULT_MUSIC_LENGTH_MS


def save_generated_prompt(result: dict) -> None:
    """Write the generated prompt as an exact /plan request body.

    The /plan endpoint accepts ``{prompt, music_length_ms}``. The /prompt response
    has no duration, so it is parsed from the prompt text (or defaulted).
    test_plan_endpoint.py loads this file to plan the exact prompt produced here.
    """
    prompt_text = result["prompt"]
    plan_ready = {
        "prompt": prompt_text,
        "music_length_ms": extract_music_length_ms(prompt_text),
    }
    with open(GENERATED_PROMPT_PATH, "w", encoding="utf-8") as f:
        json.dump(plan_ready, f, indent=2)
    print(f"\n💾 Saved plan-ready prompt to: {GENERATED_PROMPT_PATH.name} "
          f"(music_length_ms={plan_ready['music_length_ms']})")
    print("   Run test_plan_endpoint.py to plan this exact prompt.")


async def test_prompt_generation():
    """Test the prompt generation endpoint with a sample request."""

    base_url = "http://localhost:8000"

    # Example request payload (loaded from prompt_test_cases.json -> "default")
    payload = load_test_data()["default"]

    print("=" * 80)
    print("Testing /prompt endpoint")
    print("=" * 80)
    print("\nRequest payload:")
    pprint(payload)
    print("\n" + "=" * 80)

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Make the request
            print("\nSending POST request to /prompt...")
            response = await client.post(f"{base_url}/prompt", json=payload)

            # Check response status
            print(f"Status code: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("\n" + "=" * 80)
                print("✓ Success! Generated prompt:")
                print("=" * 80)
                print(f"\nRequest ID: {result['request_id']}")
                print(f"Timestamp: {result['timestamp']}")
                print(f"Title: {result.get('title')}")
                print(f"Description: {result.get('description')}")
                print(f"\nPrompt ({len(result['prompt'])} characters):")
                print("-" * 80)
                print(result["prompt"])
                print("-" * 80)
                print("\nFull JSON Response:")
                print("-" * 80)
                print(json.dumps(result, indent=2))
                print("-" * 80)

                # Persist the prompt in plan-ready form for the plan endpoint test
                save_generated_prompt(result)
            else:
                print(f"\n✗ Error: {response.status_code}")
                print(response.text)

        except httpx.ConnectError:
            print("\n✗ Error: Could not connect to server.")
            print("Make sure the server is running with: uv run python main.py")
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")


async def test_all_combinations():
    """Test multiple combinations of presets."""

    base_url = "http://localhost:8000"

    # Preset combinations loaded from prompt_test_cases.json -> "cases"
    test_cases = load_test_data()["cases"]

    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, test_case in enumerate(test_cases, 1):
            print("\n" + "=" * 80)
            print(f"Test {i}/{len(test_cases)}: {test_case['name']}")
            print("=" * 80)

            try:
                response = await client.post(
                    f"{base_url}/prompt", json=test_case["payload"]
                )

                if response.status_code == 200:
                    result = response.json()
                    print(f"✓ Success! Generated {len(result['prompt'])} characters")
                    print(f"  Request ID: {result['request_id']}")
                    print("-" * 80)
                    print(result["prompt"])
                    print("-" * 80)
                else:
                    print(f"✗ Error: {response.status_code}")

            except Exception as e:
                print(f"✗ Error: {e}")

            # Small delay between requests
            await asyncio.sleep(1)


async def main():
    """Run the tests."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        await test_all_combinations()
    else:
        await test_prompt_generation()
        print("\n" + "=" * 80)
        print("Tip: Run with --all to test multiple combinations")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
