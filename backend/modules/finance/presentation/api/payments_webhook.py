"""Public webhook endpoint for the real payment gateway -- deliberately NOT
wired through require_permission, since Stripe never carries our JWTs. Trust
comes entirely from the gateway's own signature scheme, verified inside
`HandlePaymentGatewayWebhookUseCase` (via the resolved provider) before any
payload is treated as authentic. Mirrors Communication's identical
`webhooks.py` convention for the same reason.
"""
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from core.db.session import get_db
from modules.finance.application.dtos import HandlePaymentWebhookInput
from modules.finance.application.use_cases.payment_session_use_cases import HandlePaymentGatewayWebhookUseCase

router = APIRouter()


@router.post("/payments/webhooks/{provider}")
async def receive_payment_webhook(
    provider: str,
    request: Request,
    stripe_signature: str = Header(default="", alias="Stripe-Signature"),
    db: Session = Depends(get_db),
) -> dict:
    raw_body = await request.body()
    HandlePaymentGatewayWebhookUseCase(db).execute(
        HandlePaymentWebhookInput(raw_body=raw_body, signature_header=stripe_signature, provider_name=provider)
    )
    db.commit()
    return {"received": True}
