import logging
import time
import uuid
from functools import lru_cache
from typing import BinaryIO

from flask import current_app
from supabase import Client, create_client

from app.services.infrastructure_errors import is_transient_infrastructure_error

_log = logging.getLogger(__name__)

STORAGE_DOWNLOAD_MAX_ATTEMPTS = 4
STORAGE_DOWNLOAD_TIMEOUT_SEC = 120
STORAGE_DOWNLOAD_BACKOFF_SEC = (0.4, 1.0, 2.0)


class StorageNotConfiguredError(RuntimeError):
    pass


def storage_configured() -> bool:
    cfg = current_app.config
    return bool(cfg.get("SUPABASE_URL") and cfg.get("SUPABASE_SERVICE_ROLE_KEY"))


@lru_cache(maxsize=1)
def _cached_client(url: str, key: str) -> Client:
    try:
        from supabase import ClientOptions

        return create_client(
            url,
            key,
            options=ClientOptions(
                postgrest_client_timeout=STORAGE_DOWNLOAD_TIMEOUT_SEC,
                storage_client_timeout=STORAGE_DOWNLOAD_TIMEOUT_SEC,
            ),
        )
    except Exception:
        return create_client(url, key)


def reset_storage_client() -> None:
    """Drop cached Supabase client so the next call opens a fresh HTTP connection."""
    _cached_client.cache_clear()


def _client() -> Client:
    if not storage_configured():
        raise StorageNotConfiguredError("Supabase Storage is not configured.")
    cfg = current_app.config
    return _cached_client(cfg["SUPABASE_URL"], cfg["SUPABASE_SERVICE_ROLE_KEY"])


def _bucket() -> str:
    return current_app.config["SUPABASE_STORAGE_BUCKET"]


def build_object_key(owner_user_id: int, original_filename: str) -> str:
    safe = "".join(c for c in original_filename if c.isalnum() or c in "._- ")[:180] or "document"
    return f"faculty/{owner_user_id}/{uuid.uuid4().hex}/{safe}"


def upload_private_file(*, key: str, stream: BinaryIO, mime_type: str, size: int) -> None:
    client = _client()
    bucket = _bucket()
    data = stream.read()
    if len(data) != size:
        data = data[:size]
    client.storage.from_(bucket).upload(
        path=key,
        file=data,
        file_options={"content-type": mime_type, "upsert": "false"},
    )


def delete_private_file(key: str) -> None:
    try:
        _client().storage.from_(_bucket()).remove([key])
    except Exception:
        pass


def download_private_file(key: str) -> bytes:
    """Download object bytes with bounded retries on transient socket/network errors."""
    last_exc: Exception | None = None
    for attempt in range(STORAGE_DOWNLOAD_MAX_ATTEMPTS):
        try:
            client = _client()
            return client.storage.from_(_bucket()).download(key)
        except Exception as exc:
            last_exc = exc
            if not is_transient_infrastructure_error(exc) or attempt >= STORAGE_DOWNLOAD_MAX_ATTEMPTS - 1:
                raise
            reset_storage_client()
            delay = STORAGE_DOWNLOAD_BACKOFF_SEC[min(attempt, len(STORAGE_DOWNLOAD_BACKOFF_SEC) - 1)]
            _log.warning(
                "Storage download retry %s/%s for %s after %s: %s",
                attempt + 1,
                STORAGE_DOWNLOAD_MAX_ATTEMPTS,
                key,
                type(exc).__name__,
                exc,
            )
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc


def presigned_get_url(key: str, *, expires_in: int = 300) -> str:
    client = _client()
    res = client.storage.from_(_bucket()).create_signed_url(key, expires_in)
    if isinstance(res, dict):
        url = res.get("signedURL") or res.get("signedUrl")
        if url:
            return url
    raise StorageNotConfiguredError("Could not create signed URL.")