"""
Test script for the WebSocket render endpoint.

This script tests the /render/ws WebSocket endpoint by:
1. Connecting to the WebSocket
2. Receiving the "connected" message
3. Sending a composition plan
4. Receiving progress updates
5. Receiving the final result

Usage:
    pip install websockets
    python testing/test_render_websocket.py

The backend must be running: uvicorn main:app --reload
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import websockets
except ImportError:
    print("Error: websockets library not installed.")
    print("Install with: pip install websockets")
    sys.exit(1)


def load_sample_composition_plan():
    """Load the sample composition plan from prompts/sample_comp_plan.json."""
    sample_path = Path(__file__).parent.parent / "prompts" / "sample_comp_plan.json"
    with open(sample_path) as f:
        return json.load(f)


def timestamp():
    """Return current time as HH:MM:SS.mmm"""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


async def test_websocket_render():
    """Test the WebSocket render endpoint with a simple composition plan."""
    uri = "ws://localhost:8000/render/ws"

    # Load composition plan from sample file
    composition_plan = load_sample_composition_plan()
    composition_plan["title"] = "WebSocket Test Track"

    request = {
        "type": "render",
        "composition_plan": composition_plan
    }

    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!\n")

            # Receive connected message
            msg = await websocket.recv()
            data = json.loads(msg)
            print(f"[{data['type'].upper()}] {data.get('stage', '')} ({data.get('progress_percent', '')}%)")
            print(f"  Message: {data.get('message', '')}\n")

            # Send composition plan
            print("Sending composition plan...")
            await websocket.send(json.dumps(request))
            print("Composition plan sent!\n")

            # Receive progress updates until result or error
            print("Waiting for progress updates...\n")
            while True:
                msg = await websocket.recv()
                data = json.loads(msg)

                if data["type"] == "progress":
                    print(f"[{timestamp()}] PROGRESS: {data['stage']} ({data['progress_percent']}%) - {data['message']}", flush=True)
                elif data["type"] == "result":
                    print(f"\n[{timestamp()}] " + "=" * 50)
                    print(f"[{timestamp()}] RESULT: Render complete!")
                    print("=" * 60)
                    result_data = data["data"]
                    print(f"  Filename: {result_data['filename']}")
                    print(f"  File size: {result_data['file_size_bytes']} bytes")
                    print(f"  Download URL: {result_data['download_url']}")
                    print(f"  Stream URL: {result_data['stream_url']}")
                    print(f"  Request ID: {result_data['request_id']}")
                    break
                elif data["type"] == "error":
                    print(f"\n[{timestamp()}] " + "=" * 50)
                    print(f"[{timestamp()}] ERROR: {data['error_code']}")
                    print("=" * 60)
                    print(f"  Message: {data['message']}")
                    break

            print("\nTest complete!")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"Connection closed: {e}")
    except ConnectionRefusedError:
        print("Error: Could not connect to the server.")
        print("Make sure the backend is running: uvicorn main:app --reload")
    except Exception as e:
        print(f"Error: {e}")


async def test_validation_error():
    """Test that validation errors are properly returned."""
    uri = "ws://localhost:8000/render/ws"

    # Invalid composition plan (no chunks)
    request = {
        "type": "render",
        "composition_plan": {
            "title": "Invalid Test",
            "chunks": []  # Empty chunks should trigger validation error
        }
    }

    print(f"\nTesting validation error handling...")
    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            # Receive connected message
            await websocket.recv()
            print("Connected!")

            # Send invalid composition plan
            await websocket.send(json.dumps(request))
            print("Sent invalid composition plan (empty chunks)...")

            # Should receive error
            msg = await websocket.recv()
            data = json.loads(msg)

            if data["type"] == "error":
                print(f"\n[EXPECTED ERROR] {data['error_code']}")
                print(f"  Message: {data['message']}")
                print("\nValidation error test passed!")
            else:
                print(f"\nUnexpected response: {data}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("WebSocket Render Endpoint Test")
    print("=" * 60)
    print()

    # Run the main test
    asyncio.run(test_websocket_render())

    # Run validation error test
    asyncio.run(test_validation_error())
