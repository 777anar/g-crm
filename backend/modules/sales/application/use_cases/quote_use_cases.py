"""Quote use cases: create, update metadata, change status (with versioning
and slab reservation/release), and full-quote totals recomputation."""
import copy
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.catalog.infrastructure.models.slab import Slab
from modules.sales.application.dtos import (
    CreateQuoteInput,
    UpdateQuoteInput,
    UpdateQuoteStatusInput,
)
from modules.sales.application.totals import recompute_quote, recompute_section
from modules.sales.domain import events as sales_events
from modules.sales.domain.exceptions import (
    InvalidQuoteTransitionError,
    SlabConflictError,
)
from modules.sales.domain.value_objects import (
    IMMUTABLE_QUOTE_STATUSES,
    QUOTE_STATUS_ACCEPTED,
    QUOTE_STATUS_DRAFT,
    QUOTE_STATUS_EXPIRED,
    QUOTE_STATUS_REJECTED,
    QUOTE_STATUS_SENT,
    TERMINAL_QUOTE_STATUSES,
    is_valid_quote_transition,
)
from modules.sales.infrastructure.models.quote import Quote
from modules.sales.infrastructure.models.quote_section import QuoteSection
from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem
from modules.sales.infrastructure.models.quote_section_measurement import QuoteSectionMeasurement
from modules.sales.infrastructure.repositories.item_repository import ItemRepository
from modules.sales.infrastructure.repositories.measurement_repository import MeasurementRepository
from modules.sales.infrastructure.repositories.project_repository import ProjectRepository
from modules.sales.infrastructure.repositories.quote_repository import QuoteRepository
from modules.sales.infrastructure.repositories.section_repository import SectionRepository

MODULE = "sales"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CreateQuoteUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.quotes = QuoteRepository(db)

    def execute(self, data: CreateQuoteInput) -> Quote:
        project = self.projects.get(company_id=data.company_id, project_id=data.project_id)
        if project is None:
            raise NotFoundError("Project not found")

        year = _now().year
        base_number = self.quotes.next_quote_number(company_id=data.company_id, year=year)
        version = self.quotes.get_max_version(company_id=data.company_id, project_id=data.project_id) + 1
        quote_number = f"{base_number}-v{version}"

        quote = Quote(
            company_id=data.company_id,
            project_id=data.project_id,
            customer_id=project.customer_id,
            version=version,
            quote_number=quote_number,
            currency=data.currency,
            price_list_id=data.price_list_id,
            valid_until=data.valid_until,
            internal_notes=data.internal_notes,
            customer_notes=data.customer_notes,
            vat_rate=data.vat_rate,
            discount_type=data.discount_type,
            discount_value=data.discount_value,
            prepared_by=data.actor_user_id,
        )
        self.quotes.add(quote)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="quote.created",
            entity_type="quote",
            entity_id=quote.id,
            diff={"quote_number": quote_number, "version": version},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=sales_events.QUOTE_CREATED,
                company_id=data.company_id,
                payload={
                    "quote_id": str(quote.id),
                    "project_id": str(quote.project_id),
                    "customer_id": str(quote.customer_id),
                    "version": version,
                },
                published_by_module=MODULE,
            ),
            self.db,
        )
        return quote


class UpdateQuoteUseCase:
    """Update metadata fields on a DRAFT quote.
    If the quote is in an immutable status, auto-creates a new version."""

    def __init__(self, db: Session):
        self.db = db
        self.quotes = QuoteRepository(db)
        self.sections = SectionRepository(db)
        self.measurements = MeasurementRepository(db)
        self.items = ItemRepository(db)

    def execute(self, data: UpdateQuoteInput) -> Quote:
        quote = self.quotes.get(company_id=data.company_id, quote_id=data.quote_id)
        if quote is None:
            raise NotFoundError("Quote not found")

        if quote.status in IMMUTABLE_QUOTE_STATUSES:
            quote = self._fork_version(quote, data)
        else:
            self._apply_fields(quote, data)
            self._recompute_all(quote)

        self.db.flush()
        return quote

    def _apply_fields(self, quote: Quote, data: UpdateQuoteInput) -> None:
        if data.currency is not None:
            quote.currency = data.currency
        if data.price_list_id is not None:
            quote.price_list_id = data.price_list_id
        if data.valid_until is not None:
            quote.valid_until = data.valid_until
        if data.internal_notes is not None:
            quote.internal_notes = data.internal_notes
        if data.customer_notes is not None:
            quote.customer_notes = data.customer_notes
        if data.vat_rate is not None:
            quote.vat_rate = data.vat_rate
        if data.discount_type is not None:
            quote.discount_type = data.discount_type
        if data.discount_value is not None:
            quote.discount_value = data.discount_value

    def _recompute_all(self, quote: Quote) -> None:
        sections = self.sections.list_for_quote(company_id=quote.company_id, quote_id=quote.id)
        for section in sections:
            items = self.items.list_for_section(company_id=quote.company_id, section_id=section.id)
            measurements = self.measurements.list_for_section(company_id=quote.company_id, section_id=section.id)
            recompute_section(section, items, measurements)
        recompute_quote(quote, sections)

    def _fork_version(self, original: Quote, data: UpdateQuoteInput) -> Quote:
        """Deep-copy the quote as a new draft version and apply the changes."""
        year = _now().year
        # Re-use the same base number (strip the -vN suffix) to keep version lineage.
        base_number = "-".join(original.quote_number.split("-")[:-1])  # QT-2026-0042
        new_version = self.quotes.get_max_version(
            company_id=original.company_id, project_id=original.project_id
        ) + 1
        new_number = f"{base_number}-v{new_version}"

        new_quote = Quote(
            company_id=original.company_id,
            project_id=original.project_id,
            customer_id=original.customer_id,
            version=new_version,
            quote_number=new_number,
            currency=original.currency,
            price_list_id=original.price_list_id,
            valid_until=original.valid_until,
            internal_notes=original.internal_notes,
            customer_notes=original.customer_notes,
            vat_rate=original.vat_rate,
            discount_type=original.discount_type,
            discount_value=original.discount_value,
            prepared_by=original.prepared_by,
        )
        self._apply_fields(new_quote, data)
        self.quotes.add(new_quote)

        # Copy sections + items + measurements.
        orig_sections = self.sections.list_for_quote(
            company_id=original.company_id, quote_id=original.id
        )
        for orig_sec in orig_sections:
            new_sec = QuoteSection(
                company_id=original.company_id,
                quote_id=new_quote.id,
                name=orig_sec.name,
                sort_order=orig_sec.sort_order,
                notes=orig_sec.notes,
            )
            self.db.add(new_sec)
            self.db.flush()

            for orig_item in self.items.list_for_section(
                company_id=original.company_id, section_id=orig_sec.id
            ):
                self.db.add(QuoteSectionItem(
                    company_id=original.company_id,
                    section_id=new_sec.id,
                    quote_id=new_quote.id,
                    item_type=orig_item.item_type,
                    sort_order=orig_item.sort_order,
                    description=orig_item.description,
                    material_id=orig_item.material_id,
                    slab_id=orig_item.slab_id,
                    quantity=orig_item.quantity,
                    unit=orig_item.unit,
                    unit_sale_price=orig_item.unit_sale_price,
                    unit_cost_price=orig_item.unit_cost_price,
                    line_total_sale=orig_item.line_total_sale,
                    line_total_cost=orig_item.line_total_cost,
                    notes=orig_item.notes,
                ))

            for orig_m in self.measurements.list_for_section(
                company_id=original.company_id, section_id=orig_sec.id
            ):
                self.db.add(QuoteSectionMeasurement(
                    company_id=original.company_id,
                    section_id=new_sec.id,
                    quote_id=new_quote.id,
                    sort_order=orig_m.sort_order,
                    label=orig_m.label,
                    length_mm=orig_m.length_mm,
                    width_mm=orig_m.width_mm,
                    thickness_mm=orig_m.thickness_mm,
                    quantity=orig_m.quantity,
                    area_m2=orig_m.area_m2,
                    waste_pct=orig_m.waste_pct,
                    required_area_m2=orig_m.required_area_m2,
                    override_required_area=orig_m.override_required_area,
                    notes=orig_m.notes,
                ))

        self.db.flush()

        # Recompute all totals from the copied items.
        new_sections = self.sections.list_for_quote(
            company_id=new_quote.company_id, quote_id=new_quote.id
        )
        for new_sec in new_sections:
            items = self.items.list_for_section(company_id=new_quote.company_id, section_id=new_sec.id)
            measurements = self.measurements.list_for_section(company_id=new_quote.company_id, section_id=new_sec.id)
            recompute_section(new_sec, items, measurements)
        recompute_quote(new_quote, new_sections)

        record_audit(
            self.db,
            company_id=original.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="quote.version_created",
            entity_type="quote",
            entity_id=new_quote.id,
            diff={"new_version": new_version, "parent_quote_id": str(original.id)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=sales_events.QUOTE_VERSION_CREATED,
                company_id=original.company_id,
                payload={
                    "quote_id": str(new_quote.id),
                    "project_id": str(new_quote.project_id),
                    "version": new_version,
                    "parent_version": original.version,
                },
                published_by_module=MODULE,
            ),
            self.db,
        )
        return new_quote


class UpdateQuoteStatusUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.quotes = QuoteRepository(db)
        self.items = ItemRepository(db)

    def execute(self, data: UpdateQuoteStatusInput) -> Quote:
        quote = self.quotes.get(company_id=data.company_id, quote_id=data.quote_id)
        if quote is None:
            raise NotFoundError("Quote not found")

        if not is_valid_quote_transition(current=quote.status, target=data.status):
            raise InvalidQuoteTransitionError(
                f"Cannot move quote from '{quote.status}' to '{data.status}'"
            )

        old_status = quote.status

        # Validate slab availability before accepting.
        if data.status == QUOTE_STATUS_ACCEPTED:
            self._check_slab_availability(quote)

        quote.status = data.status
        now = _now()

        if data.status == QUOTE_STATUS_SENT and quote.sent_at is None:
            quote.sent_at = now
        elif data.status == QUOTE_STATUS_ACCEPTED:
            quote.accepted_at = now
            self._reserve_slabs(quote, data.actor_user_id)
        elif data.status in TERMINAL_QUOTE_STATUSES:
            quote.rejected_at = now
            self._release_slabs(quote, data.actor_user_id)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="quote.status_changed",
            entity_type="quote",
            entity_id=quote.id,
            diff={"status": {"old": old_status, "new": quote.status}},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=sales_events.QUOTE_STATUS_CHANGED,
                company_id=data.company_id,
                payload={
                    "quote_id": str(quote.id),
                    "old_status": old_status,
                    "new_status": quote.status,
                },
                published_by_module=MODULE,
            ),
            self.db,
        )

        if data.status == QUOTE_STATUS_ACCEPTED:
            event_bus.publish(
                Event(
                    name=sales_events.QUOTE_ACCEPTED,
                    company_id=data.company_id,
                    payload={
                        "quote_id": str(quote.id),
                        "project_id": str(quote.project_id),
                        "total_final": str(quote.total_final),
                        "currency": quote.currency,
                    },
                    published_by_module=MODULE,
                ),
                self.db,
            )

        return quote

    def _check_slab_availability(self, quote: Quote) -> None:
        items = self.items.list_with_slabs_for_quote(
            company_id=quote.company_id, quote_id=quote.id
        )
        for item in items:
            slab = self.db.get(Slab, item.slab_id)
            if slab is None or slab.status != "available":
                raise SlabConflictError(
                    f"Slab {item.slab_id} is no longer available (status: {slab.status if slab else 'not found'})"
                )

    def _reserve_slabs(self, quote: Quote, actor_user_id: uuid.UUID) -> None:
        items = self.items.list_with_slabs_for_quote(
            company_id=quote.company_id, quote_id=quote.id
        )
        for item in items:
            slab = self.db.get(Slab, item.slab_id)
            if slab and slab.status == "available":
                slab.status = "reserved"
                event_bus.publish(
                    Event(
                        name=sales_events.SLAB_RESERVED,
                        company_id=quote.company_id,
                        payload={"slab_id": str(slab.id), "quote_id": str(quote.id)},
                        published_by_module=MODULE,
                    ),
                    self.db,
                )

    def _release_slabs(self, quote: Quote, actor_user_id: uuid.UUID) -> None:
        items = self.items.list_with_slabs_for_quote(
            company_id=quote.company_id, quote_id=quote.id
        )
        for item in items:
            slab = self.db.get(Slab, item.slab_id)
            if slab and slab.status == "reserved":
                slab.status = "available"
                event_bus.publish(
                    Event(
                        name=sales_events.SLAB_RELEASED,
                        company_id=quote.company_id,
                        payload={"slab_id": str(slab.id), "quote_id": str(quote.id)},
                        published_by_module=MODULE,
                    ),
                    self.db,
                )
