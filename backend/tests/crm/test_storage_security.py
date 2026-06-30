"""Covers RELEASE_CHECKLIST.md C1 (path traversal), H2 (upload size limit),
and H3 (upload RBAC)."""
import io

import pytest

from core.storage.client import sanitize_filename, new_storage_key


def test_sanitize_filename_strips_path_traversal():
    assert sanitize_filename("../../../../etc/cron.d/evil") == "evil"


def test_sanitize_filename_strips_leading_dots():
    assert sanitize_filename("..hidden") == "hidden"


def test_sanitize_filename_restricts_character_set():
    # basename() runs first, so anything before the last "/" is already
    # gone; what's left is then restricted to a safe character set.
    assert sanitize_filename("weird;name?.txt") == "weird_name_.txt"
    assert sanitize_filename("a/b/weird name*.txt") == "weird_name_.txt"


def test_sanitize_filename_never_returns_empty():
    assert sanitize_filename("../../..") == "file"
    assert sanitize_filename("") == "file"


def test_new_storage_key_cannot_escape_company_prefix():
    import uuid

    key = new_storage_key(uuid.uuid4(), "../../escape", "../../../etc/passwd")
    assert ".." not in key


def test_upload_document_with_traversal_filename_stays_within_storage_dir(app_client, owner_headers, tmp_path, monkeypatch):
    from core.storage import client as storage_client_module

    local = storage_client_module.LocalDiskStorageClient(str(tmp_path))
    monkeypatch.setattr(storage_client_module, "storage_client", local)
    monkeypatch.setattr("core.storage.router.storage_client", local)

    import uuid

    response = app_client.post(
        "/api/v1/core/documents",
        headers=owner_headers,
        data={"module": "crm", "related_entity_type": "customer", "related_entity_id": str(uuid.uuid4())},
        files={"file": ("../../../../../../tmp/evil.txt", b"pwned", "text/plain")},
    )
    assert response.status_code == 200, response.text

    # Nothing was written outside tmp_path.
    escaped = tmp_path.parent / "evil.txt"
    assert not escaped.exists()
    written_files = list(tmp_path.rglob("*evil*"))
    assert len(written_files) == 1
    assert tmp_path in written_files[0].parents


def test_upload_rejects_file_over_size_limit(app_client, owner_headers):
    import uuid
    from core.storage.router import MAX_UPLOAD_SIZE_BYTES

    oversized = io.BytesIO(b"0" * (MAX_UPLOAD_SIZE_BYTES + 1))
    response = app_client.post(
        "/api/v1/core/documents",
        headers=owner_headers,
        data={"module": "crm", "related_entity_type": "customer", "related_entity_id": str(uuid.uuid4())},
        files={"file": ("big.bin", oversized, "application/octet-stream")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_upload_requires_write_permission(app_client, viewer_headers):
    import uuid

    response = app_client.post(
        "/api/v1/core/documents",
        headers=viewer_headers,
        data={"module": "crm", "related_entity_type": "customer", "related_entity_id": str(uuid.uuid4())},
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 403


def test_upload_succeeds_for_rep_role(app_client, owner_headers):
    import uuid

    response = app_client.post(
        "/api/v1/core/documents",
        headers=owner_headers,
        data={"module": "crm", "related_entity_type": "customer", "related_entity_id": str(uuid.uuid4())},
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 200
