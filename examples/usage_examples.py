"""
Example usage of the /prompt endpoint for generating music prompts.

This script demonstrates various ways to use the API programmatically.
"""

import asyncio
import httpx
from typing import Dict, Any


# Base URL for the API
BASE_URL = "http://localhost:8000"


async def generate_simple_prompt():
    """
    Example 1: Generate a simple music prompt for an ad campaign.
    """
    print("\n" + "=" * 80)
    print("Example 1: Ad Campaign Music")
    print("=" * 80)
    
    request_data = {
        "project_blueprint": "ad_brand_fast_hook",
        "sound_profile": "bright_pop_electro",
        "delivery_and_control": "balanced_studio",
        "instrumental_only": False,
        "user_narrative": None  # No narrative for ad campaigns
    }
    
    print("\nGenerating prompt (this may take 30-60 seconds)...")
    
    # Use longer timeout since OpenAI API calls can take 30+ seconds
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(f"{BASE_URL}/prompt", json=request_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✓ Prompt generated successfully!")
            print(f"Request ID: {result['request_id']}")
            print(f"\nGenerated Prompt:\n{result['prompt'][:200]}...")
        else:
            print(f"✗ Error: {response.status_code}")
            print(response.json())


async def generate_meditation_music():
    """
    Example 2: Generate a meditation/wellness track.
    """
    print("\n" + "=" * 80)
    print("Example 2: Meditation Music")
    print("=" * 80)
    
    request_data = {
        "project_blueprint": "meditation_sleep",
        "sound_profile": "lofi_cozy",
        "delivery_and_control": "exploratory_iterate",
        "instrumental_only": True,
        "user_narrative": "A peaceful evening meditation session after a long day at work, focusing on letting go of stress and finding inner calm."
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(f"{BASE_URL}/prompt", json=request_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✓ Prompt generated successfully!")
            print(f"Request ID: {result['request_id']}")
            print(f"\nGenerated Prompt:\n{result['prompt'][:200]}...")
        else:
            print(f"✗ Error: {response.status_code}")


async def generate_game_music():
    """
    Example 3: Generate video game action music.
    """
    print("\n" + "=" * 80)
    print("Example 3: Video Game Action Music")
    print("=" * 80)
    
    request_data = {
        "project_blueprint": "video_game_action_loop",
        "sound_profile": "epic_cinematic",
        "delivery_and_control": "balanced_studio",
        "instrumental_only": True,
        "user_narrative": "An epic boss battle in a fantasy RPG. The hero faces a dragon in an ancient volcano. The music should build tension and feel heroic."
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(f"{BASE_URL}/prompt", json=request_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✓ Prompt generated successfully!")
            print(f"Request ID: {result['request_id']}")
            print(f"\nGenerated Prompt:\n{result['prompt'][:200]}...")
        else:
            print(f"✗ Error: {response.status_code}")


async def batch_generate_prompts():
    """
    Example 4: Generate multiple prompts in batch.
    """
    print("\n" + "=" * 80)
    print("Example 4: Batch Generate Multiple Prompts")
    print("=" * 80)
    
    requests = [
        {
            "name": "Podcast Intro",
            "data": {
                "project_blueprint": "podcast_voiceover_loop",
                "sound_profile": "lofi_cozy",
                "delivery_and_control": "balanced_studio",
                "instrumental_only": True,
                "user_narrative": None
            }
        },
        {
            "name": "Brand Anthem",
            "data": {
                "project_blueprint": "ad_brand_fast_hook",
                "sound_profile": "indie_live_band",
                "delivery_and_control": "balanced_studio",
                "instrumental_only": False,
                "user_narrative": None
            }
        },
        {
            "name": "Dark Trap Beat",
            "data": {
                "project_blueprint": "standalone_song_mini",
                "sound_profile": "dark_trap_night",
                "delivery_and_control": "exploratory_iterate",
                "instrumental_only": True,
                "user_narrative": "Late night in the city, neon lights reflecting off wet streets. A story of ambition and hustle."
            }
        }
    ]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, req in enumerate(requests, 1):
            print(f"\n[{i}/{len(requests)}] Generating: {req['name']}")
            
            try:
                response = await client.post(f"{BASE_URL}/prompt", json=req['data'])
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"  ✓ Success! Length: {len(result['prompt'])} chars")
                    print(f"  Request ID: {result['request_id']}")
                else:
                    print(f"  ✗ Error: {response.status_code}")
            except Exception as e:
                print(f"  ✗ Exception: {e}")
            
            # Small delay between requests
            await asyncio.sleep(0.5)


async def handle_errors():
    """
    Example 5: Demonstrate error handling.
    """
    print("\n" + "=" * 80)
    print("Example 5: Error Handling")
    print("=" * 80)
    
    # Invalid request (missing required field)
    invalid_request = {
        "project_blueprint": "ad_brand_fast_hook",
        # Missing sound_profile and delivery_and_control
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(f"{BASE_URL}/prompt", json=invalid_request)
            
            if response.status_code == 422:
                print("\n✓ Validation error handled correctly:")
                error_data = response.json()
                print(f"Status: {response.status_code}")
                print(f"Error: {error_data.get('detail', 'Unknown error')}")
            else:
                print(f"Unexpected status: {response.status_code}")
        except Exception as e:
            print(f"Exception: {e}")


async def with_custom_headers():
    """
    Example 6: Using custom request headers (e.g., request ID).
    """
    print("\n" + "=" * 80)
    print("Example 6: Custom Request Headers")
    print("=" * 80)
    
    request_data = {
        "project_blueprint": "ad_brand_fast_hook",
        "sound_profile": "bright_pop_electro",
        "delivery_and_control": "balanced_studio",
        "instrumental_only": False,
        "user_narrative": None
    }
    
    custom_request_id = "my-custom-request-id-12345"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BASE_URL}/prompt",
            json=request_data,
            headers={"X-Request-ID": custom_request_id}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✓ Prompt generated with custom request ID!")
            print(f"Sent Request ID: {custom_request_id}")
            print(f"Returned Request ID: {result['request_id']}")
            print(f"Match: {result['request_id'] == custom_request_id}")
        else:
            print(f"✗ Error: {response.status_code}")


async def main():
    """
    Run all examples.
    """
    print("\n" + "=" * 80)
    print("ElevenLabs Music Prompt Generator - Usage Examples")
    print("=" * 80)
    print("\nMake sure the server is running: uv run python main.py")
    print("\nNote: Each request may take 30-60 seconds due to OpenAI API processing time.")
    print("=" * 80)
    
    try:
        # Check if server is running
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(BASE_URL)
            if response.status_code != 200:
                print("\n✗ Server not responding correctly")
                return
    except httpx.ConnectError:
        print("\n✗ Error: Cannot connect to server at", BASE_URL)
        print("Please start the server with: uv run python main.py")
        return
    
    # Run examples
    await generate_simple_prompt()
    await asyncio.sleep(1)
    
    await generate_meditation_music()
    await asyncio.sleep(1)
    
    await generate_game_music()
    await asyncio.sleep(1)
    
    await batch_generate_prompts()
    await asyncio.sleep(1)
    
    await handle_errors()
    await asyncio.sleep(1)
    
    await with_custom_headers()
    
    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
