from sqlalchemy.orm import Session

from core.audit.service import record_audit
from modules.sales.application.dtos import UpsertServicePriceInput
from modules.sales.infrastructure.models.company_service_price import CompanyServicePrice
from modules.sales.infrastructure.repositories.service_price_repository import ServicePriceRepository

MODULE = "sales"


class UpsertServicePriceUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ServicePriceRepository(db)

    def execute(self, data: UpsertServicePriceInput) -> CompanyServicePrice:
        row = self.repo.upsert(
            company_id=data.company_id,
            service_key=data.service_key,
            sale_price=data.sale_price,
            cost_price=data.cost_price,
        )
        record_audit(self.db, company_id=data.company_id, module=MODULE, actor_user_id=data.actor_user_id,
                     action="service_price.upserted", entity_type="service_price", entity_id=row.id,
                     diff={"service_key": data.service_key})
        self.db.flush()
        return row
