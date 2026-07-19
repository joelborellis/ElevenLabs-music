"""
Offline round-trip test for the storage backend + metadata DB layer.

Exercises LocalStorageBackend (save/stream/get/exists/delete) and the render
repository (create / get_by_id / get_by_filename) against a temporary SQLite
database and a temporary storage directory. No server, ElevenLabs, or network
required.

Run:
    uv run python testing/test_storage_and_db.py
"""

import asyncio
import os
import sys
import tempfile
import uuid
from pathlib import Path

# Ensure the project root is importable when run directly.
sys.path.insert(0, str(Path(__file__).parent.parent))


def _configure_temp_env(tmp: Path) -> None:
    """Point config at a temp SQLite DB and local storage dir BEFORE importing app modules."""
    os.environ["STORAGE_BACKEND"] = "local"
    os.environ["LOCAL_STORAGE_DIR"] = str(tmp / "music")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(tmp / 'test.db').as_posix()}"


async def _run(tmp: Path) -> None:
    # Imported here so the temp env vars above are picked up by config.Settings().
    from db.database import init_db, dispose_db, get_sessionmaker
    from services.storage import LocalStorageBackend
    from services.render_service import RenderResult
    from services import render_repository as repo
    from models.render import RenderRequest

    # --- Storage backend round-trip ---
    storage = LocalStorageBackend(base_dir=str(tmp / "music"))
    key = f"test_track_{uuid.uuid4().hex[:8]}.mp3"
    payload = b"ID3fake-mp3-bytes-for-testing" * 100

    url = storage.save(key, payload, "audio/mpeg")
    assert url, "save() should return a URL/URI"
    assert storage.exists(key), "object should exist after save"
    assert storage.get_bytes(key) == payload, "get_bytes should round-trip"

    streamed = b"".join(storage.open_stream(key))
    assert streamed == payload, "open_stream should yield the exact bytes"
    print(f"[storage] save/exists/get/stream OK ({len(payload)} bytes, key={key})")

    # --- DB init + migration-less create_all ---
    await init_db(create_all=True)

    # --- Repository round-trip ---
    result = RenderResult(
        id=str(uuid.uuid4()),
        filename=key,
        blob_key=key,
        content_type="audio/mpeg",
        file_size_bytes=len(payload),
        blob_url=url,
        duration_ms=30000,
        composition_plan={"chunks": [{"duration_ms": 30000}]},
        song_metadata={"title": "Test"},
    )
    request = RenderRequest(prompt="a test track", music_length_ms=30000, title="Test")

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        row = await repo.create_render(session, result, request, request_id="req-123")
        assert row.id == result.id

    async with sessionmaker() as session:
        by_id = await repo.get_by_id(session, result.id)
        assert by_id is not None and by_id.blob_key == key
        assert by_id.mode == "prompt"
        assert by_id.request_id == "req-123"
        assert by_id.duration_ms == 30000

        by_name = await repo.get_by_filename(session, key)
        assert by_name is not None and by_name.id == result.id

        missing = await repo.get_by_id(session, "does-not-exist")
        assert missing is None
    print("[db] create/get_by_id/get_by_filename OK")

    # --- Delete ---
    storage.delete(key)
    assert not storage.exists(key), "object should be gone after delete"
    print("[storage] delete OK")

    await dispose_db()
    print("\nAll storage + DB round-trip checks passed.")


def main() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _configure_temp_env(tmp)
        asyncio.run(_run(tmp))


if __name__ == "__main__":
    main()
