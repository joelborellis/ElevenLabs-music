"""
Test script for the /render endpoint.
"""

import requests
import json
import os

BASE_URL = "http://localhost:8000"

# Sample composition plan for testing (music_v2 chunks format)
SAMPLE_COMPOSITION_PLAN = {
    "chunks": [
        {
            "text": "[Intro]",
            "positive_styles": [
                "95 bpm",
                "indie pop",
                "live band feel",
                "clean electric guitar riff",
                "minimal instrumentation",
                "light hi-hat tap"
            ],
            "negative_styles": [
                "full band",
                "vocals",
                "heavy bass",
                "heavy reverb"
            ],
            "duration_ms": 4000,
            "context_adherence": "high"
        },
        {
            "text": "[Verse 1]\nEmpty street starts to bloom,\nchasing shadows from the room.",
            "positive_styles": [
                "95 bpm",
                "warm male vocal",
                "authentic delivery",
                "steady bassline enters",
                "simple drum groove",
                "light rhodes keyboard chords"
            ],
            "negative_styles": [
                "shouting",
                "complex harmonies",
                "distorted guitar"
            ],
            "duration_ms": 7000,
            "context_adherence": "high"
        },
        {
            "text": "[Chorus]\nOh, the sun is breaking through.",
            "positive_styles": [
                "95 bpm",
                "uplifting energy",
                "brighter vocal tone",
                "fuller drum pattern with crash cymbal",
                "more active guitar strumming",
                "resolute feel"
            ],
            "negative_styles": [
                "minimalist",
                "slow tempo",
                "somber mood"
            ],
            "duration_ms": 5000,
            "context_adherence": "high"
        },
        {
            "text": "[Outro]",
            "positive_styles": [
                "95 bpm",
                "clean final chord",
                "resolute ending",
                "bass and drums stop together",
                "guitar note sustains and fades"
            ],
            "negative_styles": [
                "long fade out",
                "abrupt cut",
                "vocals"
            ],
            "duration_ms": 3000,
            "context_adherence": "high"
        }
    ]
}


def test_render_endpoint():
    """Test the /render endpoint with a sample composition plan."""
    
    url = f"{BASE_URL}/render"
    
    print(f"Testing POST {url}")
    print(f"Composition plan chunks: {len(SAMPLE_COMPOSITION_PLAN['chunks'])}")
    print("-" * 50)
    
    try:
        response = requests.post(url, json=SAMPLE_COMPOSITION_PLAN, timeout=300)
        response.raise_for_status()
        
        result = response.json()
        print(f"Status: {response.status_code}")
        print("\n" + "=" * 60)
        print("FULL RESPONSE DETAILS")
        print("=" * 60)
        
        # Print each top-level key and its value
        for key, value in result.items():
            print(f"\n--- {key} ---")
            if isinstance(value, dict):
                print(json.dumps(value, indent=2))
            elif isinstance(value, list):
                print(json.dumps(value, indent=2))
            else:
                print(value)
        
        print("\n" + "=" * 60)
        print("RAW JSON RESPONSE")
        print("=" * 60)
        print(json.dumps(result, indent=2))
        
        # Validate response structure
        assert "filename" in result, "Response missing 'filename'"
        assert "file_path" in result, "Response missing 'file_path'"
        assert "download_url" in result, "Response missing 'download_url'"
        assert "file_size_bytes" in result, "Response missing 'file_size_bytes'"
        assert "request_id" in result, "Response missing 'request_id'"
        
        print("\n✅ Render test passed!")
        return result
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to server. Is it running?")
        return None
    except requests.exceptions.Timeout:
        print("❌ Error: Request timed out. Rendering may take a while.")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"Response: {response.text}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_download_endpoint(filename: str):
    """Test the /render/download/{filename} endpoint."""
    
    url = f"{BASE_URL}/render/download/{filename}"
    
    print(f"\nTesting GET {url}")
    print("-" * 50)
    
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        print(f"Content-Type: {content_type}")
        
        # Save to local file for verification
        output_dir = os.path.join(os.path.dirname(__file__), "music")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"downloaded_{filename}")
        
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = os.path.getsize(output_path)
        print(f"Downloaded file size: {file_size} bytes")
        print(f"Saved to: {output_path}")
        
        assert file_size > 0, "Downloaded file is empty"
        assert "audio" in content_type or "mpeg" in content_type, f"Unexpected content type: {content_type}"
        
        print("\n✅ Download test passed!")
        return output_path
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"Response: {response.text}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_stream_endpoint(filename: str):
    """Test the /render/stream/{filename} endpoint."""
    
    url = f"{BASE_URL}/render/stream/{filename}"
    
    print(f"\nTesting GET {url}")
    print("-" * 50)
    
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        # Check headers
        content_type = response.headers.get("Content-Type", "")
        content_length = response.headers.get("Content-Length", "unknown")
        
        print(f"Content-Type: {content_type}")
        print(f"Content-Length: {content_length}")
        
        # Read first chunk to verify streaming works
        first_chunk = next(response.iter_content(chunk_size=8192))
        print(f"First chunk size: {len(first_chunk)} bytes")
        
        assert len(first_chunk) > 0, "Stream returned empty data"
        assert "audio" in content_type or "mpeg" in content_type, f"Unexpected content type: {content_type}"
        
        print("\n✅ Stream test passed!")
        return True
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"Response: {response.text}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_download_not_found():
    """Test the /render/download endpoint with a non-existent file."""
    
    url = f"{BASE_URL}/render/download/nonexistent_file.mp3"
    
    print(f"\nTesting 404 handling - GET {url}")
    print("-" * 50)
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 404:
            print(f"✅ Correctly returned 404 for non-existent file")
            return True
        else:
            print(f"❌ Expected 404, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_render_endpoint_with_title():
    """Test the /render endpoint with a title for custom filename."""

    url = f"{BASE_URL}/render"

    payload = {
        "title": "Epic Battle Theme",  # <-- New title field
        "chunks": [
            {
                "text": "[Intro]",
                "positive_styles": ["epic", "cinematic", "orchestral", "building tension", "strings"],
                "negative_styles": ["percussion", "lo-fi", "ambient"],
                "duration_ms": 5000,
                "context_adherence": "high"
            }
        ]
    }

    print(f"\nTesting POST {url} with title")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("-" * 50)

    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()

        result = response.json()
        print(f"Status: {response.status_code}")
        print(f"Response:\n{json.dumps(result, indent=2)}")

        # Verify filename contains the title
        assert "epic_battle_theme" in result["filename"].lower(), \
            f"Filename should contain title: {result['filename']}"

        print("\nTest with title passed!")
        return result

    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server.")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def test_render_validation():
    """Test the /render endpoint with invalid input."""

    url = f"{BASE_URL}/render"
    
    # Test with empty chunks - should return 422
    payload = {
        "chunks": []
    }
    
    print(f"\nTesting render with empty chunks (should return 422)")
    print("-" * 50)
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 422:
            print(f"✅ Correctly returned 422 for empty chunks")
            print(f"Response: {response.json()}")
            return True
        elif response.status_code >= 400:
            print(f"Response: {response.text[:500]}")
            return False
        else:
            print(f"❌ Expected 422, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def run_all_tests():
    """Run all render endpoint tests."""

    print("=" * 60)
    print("RENDER ENDPOINT TESTS")
    print("=" * 60)

    # Test 404 handling first (quick test)
    test_download_not_found()

    # Test render with title (custom filename)
    test_render_endpoint_with_title()

    # Test the main render endpoint
    result = test_render_endpoint()
    
    if result:
        filename = result.get("filename")
        
        if filename:
            # Test download endpoint
            test_download_endpoint(filename)
            
            # Test stream endpoint
            test_stream_endpoint(filename)
    
    # Test validation
    test_render_validation()
    
    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
