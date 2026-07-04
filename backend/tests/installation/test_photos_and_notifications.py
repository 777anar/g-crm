"""Tests for Installation photo attachments (incl. signature) and notifications."""
import io


def _upload_document(app_client, headers, *, related_entity_id: str) -> str:
    resp = app_client.post(
        "/api/v1/core/documents",
        headers=headers,
        data={"module": "installation", "related_entity_type": "installation_job", "related_entity_id": related_entity_id},
        files={"file": ("photo.png", io.BytesIO(b"fake-png-bytes"), "image/png")},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_add_photo_and_signature(app_client, owner_headers, ready_order):
    job = app_client.post(
        "/api/v1/installation/jobs", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()

    before_doc_id = _upload_document(app_client, owner_headers, related_entity_id=job["id"])
    add_resp = app_client.post(
        f"/api/v1/installation/jobs/{job['id']}/photos",
        headers=owner_headers,
        json={"document_id": before_doc_id, "photo_type": "before", "caption": "Kitchen before install"},
    )
    assert add_resp.status_code == 200, add_resp.text
    assert add_resp.json()["photo_type"] == "before"

    signature_doc_id = _upload_document(app_client, owner_headers, related_entity_id=job["id"])
    sig_resp = app_client.post(
        f"/api/v1/installation/jobs/{job['id']}/photos",
        headers=owner_headers,
        json={"document_id": signature_doc_id, "photo_type": "signature"},
    )
    assert sig_resp.status_code == 200, sig_resp.text
    assert sig_resp.json()["photo_type"] == "signature"

    list_resp = app_client.get(f"/api/v1/installation/jobs/{job['id']}/photos", headers=owner_headers)
    assert list_resp.status_code == 200
    photo_types = {p["photo_type"] for p in list_resp.json()["items"]}
    assert photo_types == {"before", "signature"}


def test_add_photo_invalid_type_returns_400(app_client, owner_headers, ready_order):
    job = app_client.post(
        "/api/v1/installation/jobs", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()
    doc_id = _upload_document(app_client, owner_headers, related_entity_id=job["id"])

    resp = app_client.post(
        f"/api/v1/installation/jobs/{job['id']}/photos",
        headers=owner_headers,
        json={"document_id": doc_id, "photo_type": "not-a-real-type"},
    )
    assert resp.status_code == 400, resp.text


def test_mark_notification_read(app_client, owner_headers, ready_order, crew, installer_user, company):
    job = app_client.post(
        "/api/v1/installation/jobs", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()
    app_client.patch(
        f"/api/v1/installation/jobs/{job['id']}", headers=owner_headers, json={"crew_id": crew["id"]}
    )

    from core.auth.models import ROLE_OWNER
    from core.auth.security import create_access_token

    installer_headers = {
        "Authorization": f"Bearer {create_access_token(user_id=installer_user.id, active_company_id=company.id, role=ROLE_OWNER)}"
    }
    notifications = app_client.get("/api/v1/installation/notifications", headers=installer_headers).json()["items"]
    assert len(notifications) == 1
    notification_id = notifications[0]["id"]

    read_resp = app_client.post(
        f"/api/v1/installation/notifications/{notification_id}/read", headers=installer_headers
    )
    assert read_resp.status_code == 200, read_resp.text
    assert read_resp.json()["read_at"] is not None

    unread = app_client.get(
        "/api/v1/installation/notifications", headers=installer_headers, params={"unread_only": True}
    ).json()["items"]
    assert unread == []
