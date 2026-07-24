"""E-signature integration (Phase 22) for installation job completion
sign-off: an alternative to capturing a signature via the frontend's canvas
SignaturePad and uploading it as an InstallationPhoto -- a real signature
request sent via `core.esignature`, tracked on the job's own `signature_*`
columns until a webhook (or, for the mock provider, our own frontend
"simulate" call) reports completion, which then creates the same
`photo_type="signature"` InstallationPhoto row the manual-capture path has
always produced."""
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError, ValidationAPIError
from core.audit.service import record_audit
from core.esignature.providers.base import ESIGNATURE_STATUS_COMPLETED, ESIGNATURE_STATUS_DECLINED
from core.esignature.registry import get_esignature_provider
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from core.storage.client import new_storage_key, storage_client
from core.storage.models import Document
from modules.crm.infrastructure.repositories.customer_repository import CustomerRepository
from modules.installation.application.dtos import (
    HandleJobSignatureWebhookInput,
    RequestJobSignatureInput,
    SimulateJobSignatureInput,
)
from modules.installation.domain import events as installation_events
from modules.installation.domain.exceptions import SignatureAttributionError
from modules.installation.domain.value_objects import PHOTO_TYPE_SIGNATURE
from modules.installation.infrastructure.models.installation_photo import InstallationPhoto
from modules.installation.infrastructure.repositories.installation_job_repository import InstallationJobRepository
from modules.installation.infrastructure.repositories.installation_photo_repository import (
    InstallationPhotoRepository,
)
from modules.orders.infrastructure.repositories.order_repository import OrderRepository

MODULE = "installation"


def _build_job_document(job, order) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Installation Completion Sign-Off", styles["Heading1"]),
        Spacer(1, 12),
        Paragraph(f"Job: {job.job_number}", styles["Normal"]),
        Paragraph(f"Order: {order.order_number}", styles["Normal"]),
        Paragraph(f"Completed: {job.completed_at or '-'}", styles["Normal"]),
        Spacer(1, 24),
        Paragraph(
            "By signing below, the customer confirms the installation above was completed satisfactorily.",
            styles["Normal"],
        ),
    ]
    doc.build(story)
    return buf.getvalue()


class RequestJobSignatureUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.jobs = InstallationJobRepository(db)
        self.orders = OrderRepository(db)

    def execute(self, data: RequestJobSignatureInput):
        job = self.jobs.get(company_id=data.company_id, job_id=data.job_id)
        if job is None:
            raise NotFoundError("Installation job not found")
        order = self.orders.get(company_id=data.company_id, order_id=job.order_id)
        if order is None:
            raise NotFoundError("Order not found")
        customer = CustomerRepository(self.db).get_model(company_id=data.company_id, customer_id=order.customer_id)
        if customer is None or not customer.email:
            raise ValidationAPIError("This order's customer has no email on file -- cannot request e-signature")

        provider = get_esignature_provider(data.provider_name)
        document_bytes = _build_job_document(job, order)
        result = provider.send_for_signature(
            document_bytes=document_bytes,
            document_name=f"installation-{job.id}.pdf",
            title=f"Installation completion sign-off -- {job.job_number}",
            message="Please review and sign to confirm your installation is complete.",
            signer_name=customer.name,
            signer_email=customer.email,
        )

        job.signature_status = result.status
        job.signature_provider = provider.name
        job.signature_provider_request_id = result.provider_request_id

        record_audit(
            self.db, company_id=data.company_id, module=MODULE, actor_user_id=data.actor_user_id,
            action="installation_job.signature_requested", entity_type="installation_job",
            entity_id=job.id, diff={"provider": provider.name},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=installation_events.JOB_SIGNATURE_REQUESTED,
                company_id=data.company_id,
                payload={"job_id": str(job.id), "provider": provider.name},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return job


def _complete_job_signature(db: Session, job, document_bytes: bytes, actor_user_id) -> None:
    key = new_storage_key(job.company_id, MODULE, f"installation-{job.id}-signed.pdf")
    storage_client.upload(key=key, content=document_bytes, mime_type="application/pdf")
    document = Document(
        company_id=job.company_id,
        module=MODULE,
        related_entity_type="installation_job",
        related_entity_id=job.id,
        storage_path=key,
        mime_type="application/pdf",
        uploaded_by=actor_user_id,
    )
    db.add(document)
    db.flush()

    photo = InstallationPhoto(
        company_id=job.company_id,
        installation_job_id=job.id,
        document_id=document.id,
        photo_type=PHOTO_TYPE_SIGNATURE,
        caption="E-signed completion document",
    )
    InstallationPhotoRepository(db).add(photo)

    job.signature_status = ESIGNATURE_STATUS_COMPLETED

    record_audit(
        db, company_id=job.company_id, module=MODULE, actor_user_id=actor_user_id,
        action="installation_job.signature_completed", entity_type="installation_job",
        entity_id=job.id, diff={"document_id": str(document.id)},
    )
    db.flush()

    event_bus.publish(
        Event(
            name=installation_events.JOB_SIGNATURE_COMPLETED,
            company_id=job.company_id,
            payload={"job_id": str(job.id), "document_id": str(document.id)},
            published_by_module=MODULE,
        ),
        db,
    )


class SimulateJobSignatureUseCase:
    """Mock-provider-only convenience, mirroring Finance's/Sales' identical
    simulate-only-for-mock guard."""

    def __init__(self, db: Session):
        self.db = db
        self.jobs = InstallationJobRepository(db)
        self.orders = OrderRepository(db)

    def execute(self, data: SimulateJobSignatureInput):
        job = self.jobs.get(company_id=data.company_id, job_id=data.job_id)
        if job is None:
            raise NotFoundError("Installation job not found")
        if job.signature_provider != "mock":
            raise ValidationAPIError("Only mock signature requests can be simulated")
        if job.signature_status == ESIGNATURE_STATUS_COMPLETED:
            return job

        if data.outcome == ESIGNATURE_STATUS_COMPLETED:
            order = self.orders.get(company_id=data.company_id, order_id=job.order_id)
            document_bytes = _build_job_document(job, order)
            _complete_job_signature(self.db, job, document_bytes, data.actor_user_id)
        else:
            job.signature_status = ESIGNATURE_STATUS_DECLINED
            self.db.flush()
        return job


class HandleJobSignatureWebhookUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.jobs = InstallationJobRepository(db)

    def execute(self, data: HandleJobSignatureWebhookInput) -> None:
        provider = get_esignature_provider(data.provider_name)
        event = provider.verify_and_parse_webhook(payload=data.payload)

        job = self.jobs.get_by_signature_provider_request_id(
            provider=provider.name, provider_request_id=event.provider_request_id
        )
        if job is None or job.signature_status == ESIGNATURE_STATUS_COMPLETED:
            return

        if event.status == ESIGNATURE_STATUS_COMPLETED:
            if job.created_by is None:
                # AuditLog.actor_user_id / Document.uploaded_by are both NOT
                # NULL -- a webhook-originated write is attributed to
                # whoever created the job, since there's no authenticated
                # staff user for an external provider callback.
                raise SignatureAttributionError(
                    "This installation job has no created_by user to attribute a webhook-originated signature to"
                )
            document_bytes = provider.download_signed_document(provider_request_id=event.provider_request_id)
            _complete_job_signature(self.db, job, document_bytes, job.created_by)
        elif event.status == ESIGNATURE_STATUS_DECLINED:
            job.signature_status = ESIGNATURE_STATUS_DECLINED
            self.db.flush()
        # else: an event this integration doesn't act on -- leave as is.
