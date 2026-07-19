"""
Offline end-to-end test of the /render HTTP layer.

Drives the real FastAPI app (router -> repository -> storage -> DB) with the
ElevenLabs call stubbed, using local filesystem storage and a temp SQLite DB.
Verifies that POST /render persists a render and returns an id, and that
GET /render/download/{id} and /stream/{id} serve the bytes — including the
legacy filename-based fallback. No server, network, or ElevenLabs key required.

Run:
    uv run python testing/test_render_http_offline.py
"""

import os
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

FAKE_AUDIO = b"ID3fake-audio-payload" * 200


def _configure_env(tmp: Path) -> None:
    os.environ["ENVIRONMENT"] = "development"  # so lifespan runs create_all
    os.environ["STORAGE_BACKEND"] = "local"
    os.environ["LOCAL_STORAGE_DIR"] = str(tmp / "music")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(tmp / 'test.db').as_posix()}"
    os.environ.setdefault("OPENAI_API_KEY", "test-key")  # required at import
    os.environ.setdefault("ELEVENLABS_API_KEY", "test-key")
    os.environ["OTEL_ENABLED"] = "false"


def _make_fake_track_details():
    """Mimic the ElevenLabs compose_detailed return object."""
    return types.SimpleNamespace(
        audio=FAKE_AUDIO,
        filename="stubbed_track.mp3",
        json={"composition_plan": {"chunks": [{"duration_ms": 5000}]},
              "song_metadata": {"title": "Stub"}},
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _configure_env(tmp)

        from fastapi.testclient import TestClient
        import main
        from services.render_service import get_render_service

        # Stub the ElevenLabs SDK call so no network/key is used.
        service = get_render_service()
        service.client = types.SimpleNamespace(
            music=types.SimpleNamespace(
                compose_detailed=lambda **kwargs: _make_fake_track_details()
            )
        )

        with TestClient(main.app) as client:
            # --- POST /render (prompt mode) ---
            resp = client.post("/render", json={
                "prompt": "an upbeat test track",
                "music_length_ms": 5000,
                "title": "My Test Song",
            })
            assert resp.status_code == 200, f"POST /render failed: {resp.status_code} {resp.text}"
            body = resp.json()
            assert body["id"], "response must include an id"
            assert body["download_url"] == f"/render/download/{body['id']}"
            assert body["stream_url"] == f"/render/stream/{body['id']}"
            assert body["file_size_bytes"] == len(FAKE_AUDIO)
            assert body["duration_ms"] == 5000
            render_id = body["id"]
            filename = body["filename"]
            print(f"[POST /render] OK -> id={render_id}, filename={filename}")

            # --- GET /render/download/{id} ---
            dl = client.get(f"/render/download/{render_id}")
            assert dl.status_code == 200, f"download by id failed: {dl.status_code}"
            assert dl.content == FAKE_AUDIO, "download bytes mismatch"
            assert dl.headers["content-type"].startswith("audio/mpeg")
            print("[GET /render/download/{id}] OK (bytes match)")

            # --- GET /render/stream/{id} ---
            st = client.get(f"/render/stream/{render_id}")
            assert st.status_code == 200, f"stream by id failed: {st.status_code}"
            assert st.content == FAKE_AUDIO, "stream bytes mismatch"
            print("[GET /render/stream/{id}] OK (bytes match)")

            # --- Legacy filename fallback ---
            fb = client.get(f"/render/download/{filename}")
            assert fb.status_code == 200, f"filename fallback failed: {fb.status_code}"
            assert fb.content == FAKE_AUDIO
            print("[GET /render/download/{filename}] backward-compat OK")

            # --- 404 for unknown id ---
            nf = client.get("/render/download/nonexistent-id")
            assert nf.status_code == 404, f"expected 404, got {nf.status_code}"
            print("[GET /render/download/<unknown>] 404 OK")

            # --- Health check reports DB healthy ---
            h = client.get("/health")
            assert h.status_code == 200, f"health failed: {h.status_code}"
            assert h.json()["dependencies"]["database"]["status"] == "healthy"
            print("[GET /health] database healthy OK")

        print("\nAll /render HTTP offline checks passed.")


if __name__ == "__main__":
    main()
