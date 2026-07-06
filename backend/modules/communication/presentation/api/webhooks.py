"""Public webhook endpoints for real providers -- deliberately NOT wired
through require_permission, since external providers (Meta, Twilio, a
generic partner system) never carry our JWTs. Trust comes entirely from
each provider's own signature scheme, verified inside the corresponding
use case before any payload is treated as authentic. This is exactly the
extension point modules/communication/presentation/api/inbound.py's
docstring anticipated back in Version 2.7: "once a real provider exists,
its webhook handler would call ReceiveInboundMessageUseCase directly
instead, under its own signature-verification, not this route."
"""
import json
import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session

from core.db.session import get_db
from modules.communication.application.use_cases._provider_resolution import decrypt_config
from modules.communication.application.use_cases.webhook_use_cases import (
    ReceiveGenericWebhookUseCase,
    ReceiveMetaWebhookUseCase,
    ReceiveTwilioWebhookUseCase,
)
from modules.communication.domain.exceptions import WebhookSignatureError
from modules.communication.infrastructure.repositories.channel_credential_repository import (
    ChannelCredentialRepository,
)
from modules.communication.infrastructure.repositories.channel_repository import ChannelRepository

router = APIRouter()


@router.get("/webhooks/meta/{channel_id}")
def verify_meta_webhook(
    channel_id: uuid.UUID,
    hub_mode: str = Query(default="", alias="hub.mode"),
    hub_verify_token: str = Query(default="", alias="hub.verify_token"),
    hub_challenge: str = Query(default="", alias="hub.challenge"),
    db: Session = Depends(get_db),
):
    """Meta's one-time webhook subscription handshake: echoes back
    hub.challenge only if hub.verify_token matches this channel's
    configured verify_token."""
    channel = ChannelRepository(db).get_by_id_any_company(channel_id)
    credential = (
        ChannelCredentialRepository(db).get_by_channel(company_id=channel.company_id, channel_id=channel_id)
        if channel
        else None
    )
    if channel is None or credential is None:
        return JSONResponse(status_code=404, content={"error": "channel not found"})

    config = decrypt_config(credential)
    if hub_mode == "subscribe" and hub_verify_token == config.get("verify_token"):
        return PlainTextResponse(hub_challenge)
    return JSONResponse(status_code=403, content={"error": "verify_token mismatch"})


@router.post("/webhooks/meta/{channel_id}")
async def receive_meta_webhook(channel_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    signature_header = request.headers.get("X-Hub-Signature-256")
    try:
        payload = json.loads(raw_body or b"{}")
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "invalid JSON"})

    try:
        result = ReceiveMetaWebhookUseCase(db).execute(
            channel_id=channel_id, raw_body=raw_body, signature_header=signature_header, payload=payload
        )
        db.commit()
        return result
    except WebhookSignatureError:
        db.commit()  # persist the logged rejection
        return JSONResponse(status_code=403, content={"error": "invalid signature"})


@router.post("/webhooks/twilio/{channel_id}")
async def receive_twilio_webhook(channel_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    form_params = {key: str(value) for key, value in form.items()}
    signature_header = request.headers.get("X-Twilio-Signature")

    try:
        result = ReceiveTwilioWebhookUseCase(db).execute(
            channel_id=channel_id, url=str(request.url), form_params=form_params, signature_header=signature_header
        )
        db.commit()
        return result
    except WebhookSignatureError:
        db.commit()
        return JSONResponse(status_code=403, content={"error": "invalid signature"})


@router.post("/webhooks/generic/{channel_id}")
async def receive_generic_webhook(channel_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    signature_header = request.headers.get("X-Signature-256")
    try:
        payload = json.loads(raw_body or b"{}")
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "invalid JSON"})

    try:
        result = ReceiveGenericWebhookUseCase(db).execute(
            channel_id=channel_id, raw_body=raw_body, signature_header=signature_header, payload=payload
        )
        db.commit()
        return result
    except WebhookSignatureError:
        db.commit()
        return JSONResponse(status_code=403, content={"error": "invalid signature"})
