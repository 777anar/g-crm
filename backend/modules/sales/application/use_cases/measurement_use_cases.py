from decimal import Decimal

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from modules.sales.application.dtos import CreateMeasurementInput, UpdateMeasurementInput
from modules.sales.application.totals import compute_measurement, recompute_quote, recompute_section
from modules.sales.infrastructure.models.quote_section_measurement import QuoteSectionMeasurement
from modules.sales.infrastructure.repositories.item_repository import ItemRepository
from modules.sales.infrastructure.repositories.measurement_repository import MeasurementRepository
from modules.sales.infrastructure.repositories.quote_repository import QuoteRepository
from modules.sales.infrastructure.repositories.section_repository import SectionRepository

MODULE = "sales"


def _sync_section_and_quote(db, section):
    items = ItemRepository(db).list_for_section(company_id=section.company_id, section_id=section.id)
    measurements = MeasurementRepository(db).list_for_section(company_id=section.company_id, section_id=section.id)
    recompute_section(section, items, measurements)
    quote = QuoteRepository(db).get(company_id=section.company_id, quote_id=section.quote_id)
    if quote:
        secs = SectionRepository(db).list_for_quote(company_id=quote.company_id, quote_id=quote.id)
        recompute_quote(quote, secs)


class CreateMeasurementUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.sections = SectionRepository(db)
        self.measurements = MeasurementRepository(db)

    def execute(self, data: CreateMeasurementInput) -> QuoteSectionMeasurement:
        section = self.sections.get(company_id=data.company_id, section_id=data.section_id)
        if section is None:
            raise NotFoundError("Section not found")

        m = QuoteSectionMeasurement(
            company_id=data.company_id,
            section_id=data.section_id,
            quote_id=section.quote_id,
            sort_order=data.sort_order,
            label=data.label,
            length_mm=data.length_mm,
            width_mm=data.width_mm,
            thickness_mm=data.thickness_mm,
            quantity=data.quantity,
            waste_pct=data.waste_pct,
            override_required_area=data.override_required_area,
            required_area_m2=data.required_area_m2 if data.override_required_area else None,
            notes=data.notes,
        )
        compute_measurement(m)
        self.measurements.add(m)
        _sync_section_and_quote(self.db, section)

        record_audit(self.db, company_id=data.company_id, module=MODULE, actor_user_id=data.actor_user_id,
                     action="measurement.created", entity_type="measurement", entity_id=m.id, diff={})
        self.db.flush()
        return m


class UpdateMeasurementUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.sections = SectionRepository(db)
        self.measurements = MeasurementRepository(db)

    def execute(self, data: UpdateMeasurementInput) -> QuoteSectionMeasurement:
        m = self.measurements.get(company_id=data.company_id, measurement_id=data.measurement_id)
        if m is None:
            raise NotFoundError("Measurement not found")

        if data.label is not None:
            m.label = data.label
        if data.length_mm is not None:
            m.length_mm = data.length_mm
        if data.width_mm is not None:
            m.width_mm = data.width_mm
        if data.thickness_mm is not None:
            m.thickness_mm = data.thickness_mm
        if data.quantity is not None:
            m.quantity = data.quantity
        if data.waste_pct is not None:
            m.waste_pct = data.waste_pct
        if data.override_required_area is not None:
            m.override_required_area = data.override_required_area
        if data.required_area_m2 is not None and m.override_required_area:
            m.required_area_m2 = data.required_area_m2
        if data.notes is not None:
            m.notes = data.notes
        if data.sort_order is not None:
            m.sort_order = data.sort_order

        compute_measurement(m)
        section = self.sections.get(company_id=m.company_id, section_id=m.section_id)
        if section:
            _sync_section_and_quote(self.db, section)
        self.db.flush()
        return m


class DeleteMeasurementUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.sections = SectionRepository(db)
        self.measurements = MeasurementRepository(db)

    def execute(self, *, company_id, actor_user_id, measurement_id) -> None:
        m = self.measurements.get(company_id=company_id, measurement_id=measurement_id)
        if m is None:
            raise NotFoundError("Measurement not found")
        section = self.sections.get(company_id=company_id, section_id=m.section_id)
        self.measurements.delete(m)
        if section:
            _sync_section_and_quote(self.db, section)
        self.db.flush()
