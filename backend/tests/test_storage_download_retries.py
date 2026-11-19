from unittest.mock import MagicMock, patch

import pytest

from app.services.infrastructure_errors import is_transient_infrastructure_error


def test_transient_detection_for_winerror():
    assert is_transient_infrastructure_error(OSError(10035, "socket")) is True


def test_download_retries_then_succeeds(app, app_ctx):
    from app.services import storage

    storage.reset_storage_client()
    calls = {"n": 0}

    def flaky_download(_key):
        calls["n"] += 1
        if calls["n"] < 2:
            raise OSError(10035, "[WinError 10035] would block")
        return b"ok-bytes"

    bucket = MagicMock()
    bucket.download.side_effect = flaky_download
    client = MagicMock()
    client.storage.from_.return_value = bucket

    with patch.object(storage, "_client", return_value=client):
        with patch.object(storage, "reset_storage_client"):
            with patch.object(storage.time, "sleep"):
                data = storage.download_private_file("faculty/1/test.pdf")
    assert data == b"ok-bytes"
    assert calls["n"] == 2