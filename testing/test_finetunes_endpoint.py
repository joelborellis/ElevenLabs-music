"""
Test script for the /finetunes endpoint.

Requires the server running (uv run python main.py).
"""

import requests

BASE_URL = "http://localhost:8000"


def test_list_finetunes():
    """List finetunes and validate the response shape used by the frontend."""
    url = f"{BASE_URL}/finetunes"
    print(f"Testing GET {url}")
    print("-" * 50)

    try:
        response = requests.get(url, params={"model_id": "music_v2"}, timeout=30)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to server. Is it running?")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}\nResponse: {response.text}")
        return None

    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"count: {data.get('count')} | has_more: {data.get('has_more')}")

    assert "finetunes" in data, "Response missing 'finetunes'"
    assert "count" in data, "Response missing 'count'"

    for ft in data["finetunes"][:5]:
        print(f"  - {ft['id']} | {ft.get('name')} | {ft.get('primary_genre')}")
        assert ft.get("id"), "Finetune missing 'id'"
        # only_completed default -> all returned should be usable
        assert ft.get("status") == "completed", f"Unexpected status: {ft.get('status')}"

    print("\n✅ Finetunes list test passed!")
    return data


if __name__ == "__main__":
    test_list_finetunes()
