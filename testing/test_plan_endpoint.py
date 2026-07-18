"""
Test script for the /plan endpoint.
"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"

# The prompt and music length for the valid request come from this JSON file
# so they can be changed without editing the script.
TEST_INPUT_PATH = Path(__file__).parent / "plan_test_input.json"

# Optional: the plan-ready prompt produced by test_prompt_endpoint.py. When
# present, it is used instead of the static plan_test_input.json.
GENERATED_PROMPT_PATH = Path(__file__).parent / "generated_prompt.json"

# The generated composition plan is written here in render-ready format so it can
# be fed straight into test_render_endpoint.py (POST /render, plan-mode).
GENERATED_PLAN_PATH = Path(__file__).parent / "generated_comp_plan.json"


def load_test_input() -> dict:
    """Return the /plan payload, preferring the prompt endpoint's output.

    If generated_prompt.json exists (written by test_prompt_endpoint.py), that
    exact prompt is planned; otherwise the static plan_test_input.json is used.
    """
    if GENERATED_PROMPT_PATH.exists():
        print(f"Using generated prompt from: {GENERATED_PROMPT_PATH.name}")
        with open(GENERATED_PROMPT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    print(f"No {GENERATED_PROMPT_PATH.name} found — using {TEST_INPUT_PATH.name}")
    with open(TEST_INPUT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_generated_plan(result: dict) -> None:
    """Write the generated plan as an exact /render request body.

    The /render endpoint (plan-mode) accepts ``{title, chunks}``, and the /plan
    response already returns ``chunks`` in the same Chunk shape, so the two line
    up directly. test_render_endpoint.py loads this file to render the exact plan
    produced here.
    """
    render_ready = {
        "title": "Plan Endpoint Generated Track",
        "chunks": result["chunks"],
    }
    with open(GENERATED_PLAN_PATH, "w", encoding="utf-8") as f:
        json.dump(render_ready, f, indent=2)
    print(f"\n💾 Saved render-ready composition plan to: {GENERATED_PLAN_PATH.name}")
    print("   Run test_render_endpoint.py to render this exact plan.")


def test_plan_endpoint():
    """Test the /plan endpoint with a sample prompt."""

    url = f"{BASE_URL}/plan"

    # Payload loaded from plan_test_input.json (prompt + music_length_ms)
    payload = load_test_input()

    print(f"Testing POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("-" * 50)

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()

        result = response.json()
        print(f"Status: {response.status_code}")
        print(f"Response:\n{json.dumps(result, indent=2)}")

        # Validate response structure - now returns plan directly
        assert "chunks" in result, "Response missing 'chunks'"
        assert isinstance(result["chunks"], list), "'chunks' should be a list"

        # Persist the plan in render-ready form for the render endpoint test
        save_generated_plan(result)

        print("\n✅ Test passed!")
        return result

    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to server. Is it running?")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"Response: {response.text}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_plan_endpoint_validation():
    """Test the /plan endpoint with invalid input."""
    
    url = f"{BASE_URL}/plan"
    
    # Test with missing prompt
    payload = {
        "music_length_ms": 10000
    }
    
    print(f"\nTesting validation - missing prompt")
    print("-" * 50)
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 422:
            print(f"✅ Validation correctly rejected missing prompt (422)")
        else:
            print(f"❌ Expected 422, got {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test with invalid music_length_ms
    payload = {
        "prompt": "Test prompt",
        "music_length_ms": 500  # Below minimum
    }
    
    print(f"\nTesting validation - invalid music_length_ms")
    print("-" * 50)
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 422:
            print(f"✅ Validation correctly rejected invalid music_length_ms (422)")
        else:
            print(f"❌ Expected 422, got {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("Testing /plan endpoint")
    print("=" * 50)
    
    # Test valid request
    test_plan_endpoint()
    
    # Test validation
    test_plan_endpoint_validation()
