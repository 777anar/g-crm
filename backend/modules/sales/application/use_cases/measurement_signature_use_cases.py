"""E-signature integration (Phase 22) for measurement sign-off: an
alternative to `UpdateProjectItemMeasurementUseCase`'s manual
customer_signature_document_id upload -- a real signature request sent via
`core.esignature`, tracked on the measurement's own `signature_*` columns
until a webhook (or, for the mock provider, our own frontend "simulate"
call) reports completion."""
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
from modules.sales.application.dtos import (
    HandleMeasurementSignatureWebhookInput,
    RequestMeasurementSignatureInput,
    SimulateMeasurementSignatureInput,
)
from modules.sales.domain import events as sales_events
from modules.sales.domain.exceptions import SignatureAttributionError
from modules.sales.domain.value_objects import MEASUREMENT_STATUS_FINAL
from modules.sales.infrastructure.repositories.project_item_measurement_repository import (
    ProjectItemMeasurementRepository,
)
from modules.sales.infrastructure.repositories.project_item_repository import ProjectItemRepository
from modules.sales.infrastructure.repositories.project_repository import ProjectRepository

MODULE = "sales"


def _build_measurement_document(measurement, item, project) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Measurement Sign-Off", styles["Heading1"]),
        Spacer(1, 12),
        Paragraph(f"Project: {project.name}", styles["Normal"]),
        Paragraph(f"Item: {item.name or item.item_type}", styles["Normal"]),
        Paragraph(
            f"Dimensions: {measurement.length_mm} x {measurement.width_mm} x {measurement.thickness_mm} mm, "
            f"quantity {measurement.quantity}",
            styles["Normal"],
        ),
        Paragraph(f"Measured by: {measurement.measurer_name or '-'} on {measurement.measured_at or '-'}", styles["Normal"]),
        Spacer(1, 24),
        Paragraph(
            "By signing below, the customer confirms the measurements above are accurate and approved for fabrication.",
            styles["Normal"],
        ),
    ]
    doc.build(story)
    return buf.getvalue()


class RequestMeasurementSignatureUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.measurements = ProjectItemMeasurementRepository(db)
        self.items = ProjectItemRepository(db)
        self.projects = ProjectRepository(db)

    def execute(self, data: RequestMeasurementSignatureInput):
        measurement = self.measurements.get(company_id=data.company_id, measurement_id=data.measurement_id)
        if measurement is None:
            raise NotFoundError("Measurement not found")
        item = self.items.get(company_id=data.company_id, item_id=measurement.project_item_id)
        if item is None:
            raise NotFoundError("Project item not found")
        project = self.projects.get(company_id=data.company_id, project_id=item.project_id)
        if project is None:
            raise NotFoundError("Project not found")
        customer = CustomerRepository(self.db).get_model(company_id=data.company_id, customer_id=project.customer_id)
        if customer is None or not customer.email:
            raise ValidationAPIError("This project's customer has no email on file -- cannot request e-signature")

        provider = get_esignature_provider(data.provider_name)
        document_bytes = _build_measurement_document(measurement, item, project)
        result = provider.send_for_signature(
            document_bytes=document_bytes,
            document_name=f"measurement-{measurement.id}.pdf",
            title=f"Measurement sign-off -- {project.name}",
            message="Please review and sign to confirm your measurements are correct.",
            signer_name=customer.name,
            signer_email=customer.email,
        )

        measurement.signature_status = result.status
        measurement.signature_provider = provider.name
        measurement.signature_provider_request_id = result.provider_request_id

        record_audit(
            self.db, company_id=data.company_id, module=MODULE, actor_user_id=data.actor_user_id,
            action="project_item.measurement_signature_requested", entity_type="project_item_measurement",
            entity_id=measurement.id, diff={"provider": provider.name},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=sales_events.MEASUREMENT_SIGNATURE_REQUESTED,
                company_id=data.company_id,
                payload={"measurement_id": str(measurement.id), "provider": provider.name},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return measurement


def _complete_measurement_signature(db: Session, measurement, document_bytes: bytes, actor_user_id) -> None:
    key = new_storage_key(measurement.company_id, MODULE, f"measurement-{measurement.id}-signed.pdf")
    storage_client.upload(key=key, content=document_bytes, mime_type="application/pdf")
    document = Document(
        company_id=measurement.company_id,
        module=MODULE,
        related_entity_type="project_item_measurement",
        related_entity_id=measurement.id,
        storage_path=key,
        mime_type="application/pdf",
        uploaded_by=actor_user_id,
    )
    db.add(document)
    db.flush()

    measurement.customer_signature_document_id = document.id
    measurement.signature_status = ESIGNATURE_STATUS_COMPLETED
    measurement.status = MEASUREMENT_STATUS_FINAL

    record_audit(
        db, company_id=measurement.company_id, module=MODULE, actor_user_id=actor_user_id,
        action="project_item.measurement_signature_completed", entity_type="project_item_measurement",
        entity_id=measurement.id, diff={"document_id": str(document.id)},
    )
    db.flush()

    event_bus.publish(
        Event(
            name=sales_events.MEASUREMENT_SIGNATURE_COMPLETED,
            company_id=measurement.company_id,
            payload={"measurement_id": str(measurement.id), "document_id": str(document.id)},
            published_by_module=MODULE,
        ),
        db,
    )


class SimulateMeasurementSignatureUseCase:
    """Mock-provider-only convenience, mirroring Finance's identical
    simulate-only-for-mock guard for payment sessions."""

    def __init__(self, db: Session):
        self.db = db
        self.measurements = ProjectItemMeasurementRepository(db)
        self.items = ProjectItemRepository(db)
        self.projects = ProjectRepository(db)

    def execute(self, data: SimulateMeasurementSignatureInput):
        measurement = self.measurements.get(company_id=data.company_id, measurement_id=data.measurement_id)
        if measurement is None:
            raise NotFoundError("Measurement not found")
        if measurement.signature_provider != "mock":
            raise ValidationAPIError("Only mock signature requests can be simulated")
        if measurement.signature_status == ESIGNATURE_STATUS_COMPLETED:
            return measurement

        if data.outcome == ESIGNATURE_STATUS_COMPLETED:
            item = self.items.get(company_id=data.company_id, item_id=measurement.project_item_id)
            project = self.projects.get(company_id=data.company_id, project_id=item.project_id)
            document_bytes = _build_measurement_document(measurement, item, project)
            _complete_measurement_signature(self.db, measurement, document_bytes, data.actor_user_id)
        else:
            measurement.signature_status = ESIGNATURE_STATUS_DECLINED
            self.db.flush()
        return measurement


class HandleMeasurementSignatureWebhookUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.measurements = ProjectItemMeasurementRepository(db)

    def execute(self, data: HandleMeasurementSignatureWebhookInput) -> None:
        provider = get_esignature_provider(data.provider_name)
        event = provider.verify_and_parse_webhook(payload=data.payload)

        measurement = self.measurements.get_by_signature_provider_request_id(
            provider=provider.name, provider_request_id=event.provider_request_id
        )
        if measurement is None or measurement.signature_status == ESIGNATURE_STATUS_COMPLETED:
            return

        if event.status == ESIGNATURE_STATUS_COMPLETED:
            if measurement.created_by is None:
                # AuditLog.actor_user_id / Document.uploaded_by are both NOT
                # NULL -- a webhook-originated write is attributed to
                # whoever recorded the measurement, since there's no
                # authenticated staff user for an external provider
                # callback.
                raise SignatureAttributionError(
                    "This measurement has no created_by user to attribute a webhook-originated signature to"
                )
            document_bytes = provider.download_signed_document(provider_request_id=event.provider_request_id)
            _complete_measurement_signature(self.db, measurement, document_bytes, measurement.created_by)
        elif event.status == ESIGNATURE_STATUS_DECLINED:
            measurement.signature_status = ESIGNATURE_STATUS_DECLINED
            self.db.flush()
        # else: an event this integration doesn't act on -- leave as is.
