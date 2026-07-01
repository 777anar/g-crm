import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.auth.models import User
from core.companies.models import Company
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.crm.infrastructure.models.customer import Customer
from modules.sales.application.pdf_generator import generate_quote_pdf
from modules.sales.domain.value_objects import QUOTE_STATUS_DRAFT
from modules.sales.infrastructure.repositories.item_repository import ItemRepository
from modules.sales.infrastructure.repositories.project_repository import ProjectRepository
from modules.sales.infrastructure.repositories.quote_repository import QuoteRepository
from modules.sales.infrastructure.repositories.section_repository import SectionRepository

router = APIRouter()


@router.get("/quotes/{quote_id}/pdf")
def download_quote_pdf(
    quote_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:read")),
) -> Response:
    quote = QuoteRepository(db).get(
        company_id=current_user.active_company_id, quote_id=quote_id
    )
    if quote is None:
        raise NotFoundError("Quote not found")

    project = ProjectRepository(db).get(
        company_id=current_user.active_company_id, project_id=quote.project_id
    )
    if project is None:
        raise NotFoundError("Project not found")

    customer = db.get(Customer, project.customer_id)
    company = db.get(Company, current_user.active_company_id)
    prepared_by = db.get(User, current_user.user_id)

    sections = SectionRepository(db).list_for_quote(
        company_id=current_user.active_company_id, quote_id=quote_id
    )
    all_items = ItemRepository(db).list_for_quote(
        company_id=current_user.active_company_id, quote_id=quote_id
    )
    items_by_section: dict = {}
    for item in all_items:
        items_by_section.setdefault(item.section_id, []).append(item)

    pdf_bytes = generate_quote_pdf(
        quote=quote,
        project_name=project.name,
        project_type=project.project_type or "",
        project_address=project.address,
        customer_name=customer.name if customer else "",
        customer_phone=getattr(customer, "phone", None),
        customer_email=getattr(customer, "email", None),
        company_name=company.name if company else "",
        company_address=None,
        company_phone=None,
        company_email=None,
        prepared_by_name=prepared_by.full_name if prepared_by else None,
        sections=sections,
        items_by_section=items_by_section,
        is_draft=(quote.status == QUOTE_STATUS_DRAFT),
    )

    filename = f"{quote.quote_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
