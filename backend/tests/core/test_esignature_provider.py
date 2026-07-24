"""Unit tests for the core e-signature provider library (Phase 22) -- a
stateless capability shared by Sales (measurement sign-off) and Installation
(job completion sign-off), analogous to core/storage's shared client."""
import json

import pytest

from core.api.errors import ForbiddenError, ServiceUnavailableError
from core.config import settings
from core.esignature.providers.base import ESIGNATURE_STATUS_COMPLETED
from core.esignature.providers.dropbox_sign_provider import DropboxSignProvider
from core.esignature.providers.mock_provider import MockESignatureProvider
from core.esignature.registry import get_esignature_provider


def test_registry_defaults_to_mock():
    provider = get_esignature_provider(None)
    assert provider.name == "mock"


def test_registry_resolves_explicit_provider_name():
    provider = get_esignature_provider("dropbox_sign")
    assert isinstance(provider, DropboxSignProvider)


def test_mock_provider_send_and_verify_round_trip():
    provider = MockESignatureProvider()
    result = provider.send_for_signature(
        document_bytes=b"pdf-bytes",
        document_name="doc.pdf",
        title="Sign this",
        message="Please sign",
        signer_name="Jane Doe",
        signer_email="jane@example.com",
    )
    assert result.provider_request_id.startswith("mock-")

    payload = json.dumps({"provider_request_id": result.provider_request_id, "status": "completed"})
    event = provider.verify_and_parse_webhook(payload=payload)
    assert event.status == ESIGNATURE_STATUS_COMPLETED
    assert event.provider_request_id == result.provider_request_id


def test_dropbox_sign_provider_raises_when_not_configured():
    provider = DropboxSignProvider()
    with pytest.raises(ServiceUnavailableError):
        provider.send_for_signature(
            document_bytes=b"pdf-bytes",
            document_name="doc.pdf",
            title="Sign this",
            message="Please sign",
            signer_name="Jane Doe",
            signer_email="jane@example.com",
        )


def test_dropbox_sign_provider_rejects_invalid_webhook_signature(monkeypatch):
    monkeypatch.setattr(settings, "esignature_api_key", "test-api-key")
    provider = DropboxSignProvider()
    payload = json.dumps(
        {
            "event": {"event_time": "1234567890", "event_type": "signature_request_signed", "event_hash": "wrong-hash"},
            "signature_request": {"signature_request_id": "abc123"},
        }
    )
    with pytest.raises(ForbiddenError):
        provider.verify_and_parse_webhook(payload=payload)
