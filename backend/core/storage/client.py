"""Storage client wrapper. Uses Supabase Storage when configured; falls back
to local disk for development so the platform runs without external
dependencies during early Phase 1 work. Both implementations satisfy the same
interface so callers never branch on which backend is active."""
import os
import re
import uuid
from abc import ABC, abstractmethod

from core.config import settings

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
# Stricter than the filename pattern: module is a raw path *segment* (never
# basename()'d), so dots are disallowed entirely -- otherwise "..", "...",
# etc. could reconstruct a traversal sequence once joined with "/".
_SAFE_PATH_SEGMENT_RE = re.compile(r"[^A-Za-z0-9_-]+")


class StorageClient(ABC):
    @abstractmethod
    def upload(self, *, key: str, content: bytes, mime_type: str) -> str:
        ...

    @abstractmethod
    def get_signed_url(self, *, key: str, expires_in_seconds: int = 3600) -> str:
        ...


class LocalDiskStorageClient(StorageClient):
    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def upload(self, *, key: str, content: bytes, mime_type: str) -> str:
        base_dir = os.path.abspath(self.base_dir)
        path = os.path.abspath(os.path.join(base_dir, key))
        # Defense-in-depth: even though new_storage_key() sanitizes its inputs,
        # refuse to write anywhere outside the configured storage directory.
        if os.path.commonpath([base_dir, path]) != base_dir:
            raise ValueError(f"Refusing to write outside storage directory: {key}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
        return key

    def get_signed_url(self, *, key: str, expires_in_seconds: int = 3600) -> str:
        return f"file://{os.path.join(self.base_dir, key)}"


class SupabaseStorageClient(StorageClient):
    def __init__(self, url: str, service_key: str, bucket: str) -> None:
        from supabase import create_client

        self._client = create_client(url, service_key)
        self._bucket = bucket

    def upload(self, *, key: str, content: bytes, mime_type: str) -> str:
        self._client.storage.from_(self._bucket).upload(
            key, content, {"content-type": mime_type, "upsert": "true"}
        )
        return key

    def get_signed_url(self, *, key: str, expires_in_seconds: int = 3600) -> str:
        result = self._client.storage.from_(self._bucket).create_signed_url(key, expires_in_seconds)
        return result.get("signedURL") or result.get("signed_url")


def build_storage_client() -> StorageClient:
    if settings.supabase_url and settings.supabase_service_key:
        return SupabaseStorageClient(
            settings.supabase_url, settings.supabase_service_key, settings.supabase_storage_bucket
        )
    return LocalDiskStorageClient(settings.local_storage_dir)


storage_client = build_storage_client()


def sanitize_filename(filename: str) -> str:
    """Strips any directory components and restricts to a safe character set,
    preventing path traversal (e.g. "../../etc/cron.d/evil") from reaching a
    storage key that gets joined onto a real filesystem path. Always returns
    a non-empty name."""
    base = os.path.basename(filename or "")
    base = base.lstrip(".")  # drop leading dots so ".." / hidden-file tricks can't survive basename()
    safe = _SAFE_FILENAME_RE.sub("_", base)[:200]
    return safe or "file"


def new_storage_key(company_id: uuid.UUID, module: str, filename: str) -> str:
    safe_module = _SAFE_PATH_SEGMENT_RE.sub("_", module or "misc")[:50] or "misc"
    return f"{company_id}/{safe_module}/{uuid.uuid4()}-{sanitize_filename(filename)}"
