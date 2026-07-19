"""
Storage abstraction for rendered audio files.

Rendered audio bytes are large binary blobs and must NOT live in the metadata
database. This module provides a small ``StorageBackend`` interface with two
implementations:

- ``LocalStorageBackend`` — writes to the local filesystem (``output/music``).
  Dev/offline default; preserves the project's original behavior.
- ``AzureBlobStorageBackend`` — stores objects in Azure Blob Storage. Authenticates
  with a connection string when one is configured (reliable local dev) and
  otherwise with managed identity via ``DefaultAzureCredential`` (keyless in
  Azure Container Apps).

The backend is selected by ``settings.storage_backend`` and exposed as a
singleton via ``get_storage_backend()`` (mirrors ``get_render_service()``).
"""

import logging
from pathlib import Path
from typing import Iterator, Optional, Protocol, runtime_checkable

from config import settings

logger = logging.getLogger(__name__)

# Chunk size for streaming reads (matches the previous inline value in the router).
_STREAM_CHUNK_SIZE = 8192


@runtime_checkable
class StorageBackend(Protocol):
    """Interface for persisting and serving rendered audio objects."""

    def save(self, key: str, data: bytes, content_type: str) -> str:
        """Persist ``data`` under ``key`` and return a canonical URL/URI reference."""
        ...

    def open_stream(self, key: str) -> Iterator[bytes]:
        """Yield the object's bytes in chunks (for a StreamingResponse)."""
        ...

    def get_bytes(self, key: str) -> Optional[bytes]:
        """Return the full object bytes, or None if the key does not exist."""
        ...

    def delete(self, key: str) -> None:
        """Delete the object. No-op if it does not exist."""
        ...

    def exists(self, key: str) -> bool:
        """Return True if an object exists under ``key``."""
        ...


class LocalStorageBackend:
    """Filesystem-backed storage under ``settings.local_storage_dir``.

    Object ``key`` values may contain forward-slash prefixes (e.g.
    ``music/foo_ab12cd34.mp3``); these map to subdirectories under the base dir.
    """

    def __init__(self, base_dir: Optional[str] = None):
        base = base_dir or settings.local_storage_dir
        # Resolve relative to the project root (parent of this services/ package).
        root = Path(__file__).parent.parent
        self.base_dir = (root / base).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalStorageBackend base directory: {self.base_dir}")

    def _path_for(self, key: str) -> Path:
        return self.base_dir / key

    def save(self, key: str, data: bytes, content_type: str) -> str:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        logger.info(f"Saved {len(data)} bytes to {path}")
        return path.as_uri()

    def open_stream(self, key: str) -> Iterator[bytes]:
        path = self._path_for(key)
        with open(path, "rb") as f:
            while chunk := f.read(_STREAM_CHUNK_SIZE):
                yield chunk

    def get_bytes(self, key: str) -> Optional[bytes]:
        path = self._path_for(key)
        if not path.exists():
            return None
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path_for(key)
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    def exists(self, key: str) -> bool:
        return self._path_for(key).exists()


class AzureBlobStorageBackend:
    """Azure Blob Storage backend.

    Auth precedence:
    1. ``AZURE_STORAGE_CONNECTION_STRING`` if set (local dev; no ``az login``).
    2. ``AZURE_STORAGE_ACCOUNT_URL`` + ``DefaultAzureCredential`` (managed identity).
    """

    def __init__(
        self,
        account_url: Optional[str] = None,
        connection_string: Optional[str] = None,
        container: Optional[str] = None,
    ):
        # Imported lazily so the Azure SDK is only required when this backend is used.
        from azure.storage.blob import BlobServiceClient

        self.container_name = container or settings.azure_storage_container
        conn = connection_string or settings.azure_storage_connection_string
        url = account_url or settings.azure_storage_account_url

        if conn:
            self.service_client = BlobServiceClient.from_connection_string(conn)
            logger.info("AzureBlobStorageBackend using connection string auth")
        elif url:
            from azure.identity import DefaultAzureCredential

            self.service_client = BlobServiceClient(
                account_url=url, credential=DefaultAzureCredential()
            )
            logger.info(f"AzureBlobStorageBackend using managed identity for {url}")
        else:
            raise RuntimeError(
                "AzureBlobStorageBackend requires AZURE_STORAGE_CONNECTION_STRING "
                "or AZURE_STORAGE_ACCOUNT_URL to be configured."
            )

        self.container_client = self.service_client.get_container_client(
            self.container_name
        )
        self._ensure_container()

    def _ensure_container(self) -> None:
        """Create the container if it does not already exist."""
        from azure.core.exceptions import ResourceExistsError

        try:
            self.container_client.create_container()
            logger.info(f"Created blob container '{self.container_name}'")
        except ResourceExistsError:
            logger.debug(f"Blob container '{self.container_name}' already exists")

    def save(self, key: str, data: bytes, content_type: str) -> str:
        from azure.storage.blob import ContentSettings

        blob_client = self.container_client.get_blob_client(key)
        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        logger.info(f"Uploaded {len(data)} bytes to blob '{key}'")
        return blob_client.url

    def open_stream(self, key: str) -> Iterator[bytes]:
        downloader = self.container_client.download_blob(key)
        yield from downloader.chunks()

    def get_bytes(self, key: str) -> Optional[bytes]:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            return self.container_client.download_blob(key).readall()
        except ResourceNotFoundError:
            return None

    def delete(self, key: str) -> None:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            self.container_client.delete_blob(key)
        except ResourceNotFoundError:
            pass

    def exists(self, key: str) -> bool:
        return self.container_client.get_blob_client(key).exists()


# Singleton instance
_storage_backend: Optional[StorageBackend] = None


def _build_backend() -> StorageBackend:
    backend = settings.storage_backend.lower()
    if backend == "azure":
        return AzureBlobStorageBackend()
    if backend == "local":
        return LocalStorageBackend()
    raise RuntimeError(
        f"Unknown STORAGE_BACKEND '{settings.storage_backend}'. Use 'local' or 'azure'."
    )


def get_storage_backend() -> StorageBackend:
    """Get the singleton storage backend selected by ``settings.storage_backend``."""
    global _storage_backend
    if _storage_backend is None:
        _storage_backend = _build_backend()
    return _storage_backend
