import uuid
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.sales.infrastructure.models.company_service_price import CompanyServicePrice


class ServicePriceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, *, company_id: uuid.UUID, service_key: str) -> Optional[CompanyServicePrice]:
        return self.db.scalar(
            select(CompanyServicePrice).where(
                CompanyServicePrice.company_id == company_id,
                CompanyServicePrice.service_key == service_key,
            )
        )

    def list_for_company(self, *, company_id: uuid.UUID) -> List[CompanyServicePrice]:
        return list(
            self.db.scalars(
                select(CompanyServicePrice)
                .where(CompanyServicePrice.company_id == company_id)
                .order_by(CompanyServicePrice.service_key.asc())
            ).all()
        )

    def as_dict(self, *, company_id: uuid.UUID) -> Dict[str, CompanyServicePrice]:
        rows = self.list_for_company(company_id=company_id)
        return {r.service_key: r for r in rows}

    def upsert(self, *, company_id: uuid.UUID, service_key: str, sale_price, cost_price) -> CompanyServicePrice:
        row = self.get(company_id=company_id, service_key=service_key)
        if row is None:
            row = CompanyServicePrice(company_id=company_id, service_key=service_key)
            self.db.add(row)
        row.sale_price = sale_price
        row.cost_price = cost_price
        self.db.flush()
        return row
