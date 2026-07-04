from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from core.api.errors import ValidationAPIError
from core.companies.models import Company
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.reports.application.dtos import ReportFilterInput
from modules.reports.application.excel_report_generator import generate_report_excel
from modules.reports.application.export_adapter import build_export_sections
from modules.reports.application.pdf_report_generator import generate_report_pdf
from modules.reports.application.use_cases import (
    ExecutiveDashboardUseCase,
    FinanceAnalyticsUseCase,
    InstallationAnalyticsUseCase,
    ProductionAnalyticsUseCase,
    SalesAnalyticsUseCase,
)
from modules.reports.domain.value_objects import (
    DEFAULT_REPORT_PERIOD,
    VALID_EXPORT_FORMATS,
    VALID_REPORT_TYPES,
    resolve_date_range,
)
from modules.reports.presentation.schemas.reports import (
    ExecutiveDashboardOut,
    FinanceAnalyticsOut,
    InstallationAnalyticsOut,
    ProductionAnalyticsOut,
    SalesAnalyticsOut,
)

router = APIRouter()

_USE_CASES = {
    "executive": ExecutiveDashboardUseCase,
    "sales": SalesAnalyticsUseCase,
    "production": ProductionAnalyticsUseCase,
    "installation": InstallationAnalyticsUseCase,
    "finance": FinanceAnalyticsUseCase,
}


def _filter_input(
    *,
    current_user: CurrentUser,
    period: str,
    date_from: Optional[date],
    date_to: Optional[date],
) -> ReportFilterInput:
    date_range = resolve_date_range(period=period, date_from=date_from, date_to=date_to)
    return ReportFilterInput(company_id=current_user.active_company_id, date_range=date_range)


@router.get("/executive", response_model=ExecutiveDashboardOut)
def get_executive_dashboard(
    period: str = Query(default=DEFAULT_REPORT_PERIOD),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:read")),
) -> ExecutiveDashboardOut:
    data = ExecutiveDashboardUseCase(db).execute(
        _filter_input(current_user=current_user, period=period, date_from=date_from, date_to=date_to)
    )
    return ExecutiveDashboardOut(**data)


@router.get("/sales", response_model=SalesAnalyticsOut)
def get_sales_analytics(
    period: str = Query(default=DEFAULT_REPORT_PERIOD),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:read")),
) -> SalesAnalyticsOut:
    data = SalesAnalyticsUseCase(db).execute(
        _filter_input(current_user=current_user, period=period, date_from=date_from, date_to=date_to)
    )
    return SalesAnalyticsOut(**data)


@router.get("/production", response_model=ProductionAnalyticsOut)
def get_production_analytics(
    period: str = Query(default=DEFAULT_REPORT_PERIOD),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:read")),
) -> ProductionAnalyticsOut:
    data = ProductionAnalyticsUseCase(db).execute(
        _filter_input(current_user=current_user, period=period, date_from=date_from, date_to=date_to)
    )
    return ProductionAnalyticsOut(**data)


@router.get("/installation", response_model=InstallationAnalyticsOut)
def get_installation_analytics(
    period: str = Query(default=DEFAULT_REPORT_PERIOD),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:read")),
) -> InstallationAnalyticsOut:
    data = InstallationAnalyticsUseCase(db).execute(
        _filter_input(current_user=current_user, period=period, date_from=date_from, date_to=date_to)
    )
    return InstallationAnalyticsOut(**data)


@router.get("/finance", response_model=FinanceAnalyticsOut)
def get_finance_analytics(
    period: str = Query(default=DEFAULT_REPORT_PERIOD),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:read")),
) -> FinanceAnalyticsOut:
    data = FinanceAnalyticsUseCase(db).execute(
        _filter_input(current_user=current_user, period=period, date_from=date_from, date_to=date_to)
    )
    return FinanceAnalyticsOut(**data)


@router.get("/{report_type}/export/{export_format}")
def export_report(
    report_type: str,
    export_format: str,
    period: str = Query(default=DEFAULT_REPORT_PERIOD),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:read")),
) -> Response:
    if report_type not in VALID_REPORT_TYPES:
        raise ValidationAPIError(f"Unknown report type: {report_type}")
    if export_format not in VALID_EXPORT_FORMATS:
        raise ValidationAPIError(f"Unknown export format: {export_format}")

    use_case_cls = _USE_CASES[report_type]
    data = use_case_cls(db).execute(
        _filter_input(current_user=current_user, period=period, date_from=date_from, date_to=date_to)
    )
    sections = build_export_sections(report_type, data)

    company = db.get(Company, current_user.active_company_id)
    company_name = company.name if company else ""
    filename_base = f"{report_type}-report-{sections.date_from}-to-{sections.date_to}"

    if export_format == "pdf":
        content = generate_report_pdf(sections=sections, company_name=company_name)
        media_type = "application/pdf"
        filename = f"{filename_base}.pdf"
    else:
        content = generate_report_excel(sections=sections, company_name=company_name)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{filename_base}.xlsx"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
