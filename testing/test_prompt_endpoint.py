"""
Simple test script to verify the /prompt endpoint works.

This script demonstrates how to use the /prompt endpoint programmatically.
"""

import asyncio
import httpx
from pprint import pprint


async def test_prompt_generation():
    """Test the prompt generation endpoint with a sample request."""
    
    base_url = "http://localhost:8000"
    
    # Example request payload
    payload = {
        "project_blueprint": "ad_brand_fast_hook",
        "sound_profile": "bright_pop_electro",
        "delivery_and_control": "balanced_studio",
        "instrumental_only": False
    }
    
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
            response = await client.post(
                f"{base_url}/prompt",
                json=payload
            )
            
            # Check response status
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("\n" + "=" * 80)
                print("✓ Success! Generated prompt:")
                print("=" * 80)
                print(f"\nRequest ID: {result['request_id']}")
                print(f"Timestamp: {result['timestamp']}")
                print(f"\nPrompt ({len(result['prompt'])} characters):")
                print("-" * 80)
                print(result['prompt'])
                print("-" * 80)
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
    
    test_cases = [
        {
            "name": "Meditation/Wellness Track",
            "payload": {
                "project_blueprint": "meditation_sleep",
                "sound_profile": "lofi_cozy",
                "delivery_and_control": "exploratory_iterate",
                "instrumental_only": True
            }
        },
        {
            "name": "Video Game Action Music",
            "payload": {
                "project_blueprint": "video_game_action_loop",
                "sound_profile": "epic_cinematic",
                "delivery_and_control": "balanced_studio",
                "instrumental_only": True
            }
        },
        {
            "name": "Podcast Background",
            "payload": {
                "project_blueprint": "podcast_voiceover_loop",
                "sound_profile": "lofi_cozy",
                "delivery_and_control": "balanced_studio",
                "instrumental_only": True
            }
        }
    ]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, test_case in enumerate(test_cases, 1):
            print("\n" + "=" * 80)
            print(f"Test {i}/{len(test_cases)}: {test_case['name']}")
            print("=" * 80)
            
            try:
                response = await client.post(
                    f"{base_url}/prompt",
                    json=test_case['payload']
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✓ Success! Generated {len(result['prompt'])} characters")
                    print(f"  Request ID: {result['request_id']}")
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
