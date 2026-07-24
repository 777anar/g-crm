"""Public webhook endpoint for the real e-signature provider -- deliberately
NOT wired through require_permission, since external e-signature providers
never carry our JWTs. Trust comes entirely from the provider's own
signature scheme, verified inside `HandleJobSignatureWebhookUseCase`.
Mirrors Communication's identical `webhooks.py` convention.
"""
from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session

from core.db.session import get_db
from modules.installation.application.dtos import HandleJobSignatureWebhookInput
from modules.installation.application.use_cases import HandleJobSignatureWebhookUseCase

router = APIRouter()


@router.post("/esignature/{provider}")
def receive_job_signature_webhook(
    provider: str,
    json_payload: str = Form(..., alias="json"),
    db: Session = Depends(get_db),
) -> dict:
    HandleJobSignatureWebhookUseCase(db).execute(
        HandleJobSignatureWebhookInput(payload=json_payload, provider_name=provider)
    )
    db.commit()
    return {"received": True}
