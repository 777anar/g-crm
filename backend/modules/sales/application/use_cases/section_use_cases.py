from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from modules.sales.application.dtos import CreateSectionInput, UpdateSectionInput
from modules.sales.application.totals import recompute_quote, recompute_section
from modules.sales.infrastructure.models.quote_section import QuoteSection
from modules.sales.infrastructure.repositories.item_repository import ItemRepository
from modules.sales.infrastructure.repositories.measurement_repository import MeasurementRepository
from modules.sales.infrastructure.repositories.quote_repository import QuoteRepository
from modules.sales.infrastructure.repositories.section_repository import SectionRepository

MODULE = "sales"


def _recompute_quote_from_db(db, quote):
    from modules.sales.infrastructure.repositories.section_repository import SectionRepository
    from modules.sales.infrastructure.repositories.item_repository import ItemRepository
    from modules.sales.infrastructure.repositories.measurement_repository import MeasurementRepository
    secs = SectionRepository(db).list_for_quote(company_id=quote.company_id, quote_id=quote.id)
    for s in secs:
        items = ItemRepository(db).list_for_section(company_id=quote.company_id, section_id=s.id)
        measurements = MeasurementRepository(db).list_for_section(company_id=quote.company_id, section_id=s.id)
        recompute_section(s, items, measurements)
    recompute_quote(quote, secs)


class CreateSectionUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.quotes = QuoteRepository(db)
        self.sections = SectionRepository(db)

    def execute(self, data: CreateSectionInput) -> QuoteSection:
        quote = self.quotes.get(company_id=data.company_id, quote_id=data.quote_id)
        if quote is None:
            raise NotFoundError("Quote not found")

        section = QuoteSection(
            company_id=data.company_id,
            quote_id=data.quote_id,
            name=data.name,
            sort_order=data.sort_order,
            notes=data.notes,
        )
        self.sections.add(section)
        record_audit(self.db, company_id=data.company_id, module=MODULE, actor_user_id=data.actor_user_id,
                     action="section.created", entity_type="quote_section", entity_id=section.id,
                     diff={"name": section.name})
        self.db.flush()
        return section


class UpdateSectionUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.quotes = QuoteRepository(db)
        self.sections = SectionRepository(db)

    def execute(self, data: UpdateSectionInput) -> QuoteSection:
        section = self.sections.get(company_id=data.company_id, section_id=data.section_id)
        if section is None:
            raise NotFoundError("Section not found")
        if data.name is not None:
            section.name = data.name
        if data.sort_order is not None:
            section.sort_order = data.sort_order
        if data.notes is not None:
            section.notes = data.notes
        self.db.flush()
        return section


class DeleteSectionUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.quotes = QuoteRepository(db)
        self.sections = SectionRepository(db)

    def execute(self, *, company_id, actor_user_id, section_id) -> None:
        section = self.sections.get(company_id=company_id, section_id=section_id)
        if section is None:
            raise NotFoundError("Section not found")
        quote = self.quotes.get(company_id=company_id, quote_id=section.quote_id)
        self.sections.delete(section)
        if quote:
            _recompute_quote_from_db(self.db, quote)
        self.db.flush()
