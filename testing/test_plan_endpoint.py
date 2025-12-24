"""
Test script for the /plan endpoint.
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_plan_endpoint():
    """Test the /plan endpoint with a sample prompt."""
    
    url = f"{BASE_URL}/plan"
    
    payload = {
        "prompt": "Create an uplifting electronic pop track with a catchy hook, suitable for a brand advertisement. It should be energetic, euphoric, and radio-polished with a 4/4 time signature.",
        "music_length_ms": 10000
    }
    
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
        assert "positive_global_styles" in result, "Response missing 'positive_global_styles'"
        assert "negative_global_styles" in result, "Response missing 'negative_global_styles'"
        assert "sections" in result, "Response missing 'sections'"
        
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
