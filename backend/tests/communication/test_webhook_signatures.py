"""Pure signature-verification unit tests -- Meta's X-Hub-Signature-256
(HMAC-SHA256), Twilio's X-Twilio-Signature (HMAC-SHA1, base64), and our own
generic webhook provider's X-Signature-256. No DB/HTTP involved."""
import base64
import hashlib
import hmac

from modules.communication.infrastructure.providers.meta_client import verify_meta_signature
from modules.communication.infrastructure.providers.twilio_sms_provider import verify_twilio_signature
from modules.communication.infrastructure.providers.webhook_provider import sign_webhook_payload, verify_webhook_signature


def test_meta_signature_valid():
    secret = "app-secret"
    body = b'{"entry": []}'
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    header = f"sha256={digest}"
    assert verify_meta_signature(app_secret=secret, raw_body=body, signature_header=header) is True


def test_meta_signature_invalid_when_body_tampered():
    secret = "app-secret"
    digest = hmac.new(secret.encode(), b'{"entry": []}', hashlib.sha256).hexdigest()
    header = f"sha256={digest}"
    tampered_body = b'{"entry": ["tampered"]}'
    assert verify_meta_signature(app_secret=secret, raw_body=tampered_body, signature_header=header) is False


def test_meta_signature_invalid_when_wrong_secret():
    digest = hmac.new(b"right-secret", b"body", hashlib.sha256).hexdigest()
    header = f"sha256={digest}"
    assert verify_meta_signature(app_secret="wrong-secret", raw_body=b"body", signature_header=header) is False


def test_meta_signature_missing_header_rejected():
    assert verify_meta_signature(app_secret="secret", raw_body=b"body", signature_header=None) is False


def test_meta_signature_missing_prefix_rejected():
    digest = hmac.new(b"secret", b"body", hashlib.sha256).hexdigest()
    assert verify_meta_signature(app_secret="secret", raw_body=b"body", signature_header=digest) is False


def test_twilio_signature_valid():
    auth_token = "twilio-auth-token"
    url = "https://example.com/api/v1/communication/webhooks/twilio/abc"
    params = {"From": "+15551234567", "Body": "Hello"}
    data = url + "".join(k + params[k] for k in sorted(params))
    expected = base64.b64encode(hmac.new(auth_token.encode(), data.encode(), hashlib.sha1).digest()).decode()
    assert verify_twilio_signature(auth_token=auth_token, url=url, form_params=params, signature_header=expected) is True


def test_twilio_signature_invalid_when_params_tampered():
    auth_token = "twilio-auth-token"
    url = "https://example.com/webhooks/twilio/abc"
    params = {"From": "+15551234567", "Body": "Hello"}
    data = url + "".join(k + params[k] for k in sorted(params))
    expected = base64.b64encode(hmac.new(auth_token.encode(), data.encode(), hashlib.sha1).digest()).decode()
    tampered_params = {"From": "+15551234567", "Body": "Goodbye"}
    assert verify_twilio_signature(auth_token=auth_token, url=url, form_params=tampered_params, signature_header=expected) is False


def test_twilio_signature_missing_header_rejected():
    assert verify_twilio_signature(auth_token="x", url="https://x", form_params={}, signature_header=None) is False


def test_generic_webhook_signature_round_trip():
    secret = "shared-secret"
    body = b'{"external_contact_id": "+15551234567", "body": "hi"}'
    signature = sign_webhook_payload(secret=secret, raw_body=body)
    assert verify_webhook_signature(secret=secret, raw_body=body, signature_header=signature) is True
    assert verify_webhook_signature(secret=secret, raw_body=body, signature_header=f"sha256={signature}") is True


def test_generic_webhook_signature_invalid_secret():
    body = b'{"body": "hi"}'
    signature = sign_webhook_payload(secret="right-secret", raw_body=body)
    assert verify_webhook_signature(secret="wrong-secret", raw_body=body, signature_header=signature) is False
