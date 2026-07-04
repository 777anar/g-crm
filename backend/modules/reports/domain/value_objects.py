"""Pure value objects for the Reports module. No framework/DB imports."""
from dataclasses import dataclass
from datetime import date, timedelta

REPORT_PERIOD_7D = "7d"
REPORT_PERIOD_30D = "30d"
REPORT_PERIOD_90D = "90d"
REPORT_PERIOD_12M = "12m"
REPORT_PERIOD_CUSTOM = "custom"

VALID_REPORT_PERIODS = {
    REPORT_PERIOD_7D,
    REPORT_PERIOD_30D,
    REPORT_PERIOD_90D,
    REPORT_PERIOD_12M,
    REPORT_PERIOD_CUSTOM,
}

DEFAULT_REPORT_PERIOD = REPORT_PERIOD_30D

_PERIOD_DAYS = {
    REPORT_PERIOD_7D: 7,
    REPORT_PERIOD_30D: 30,
    REPORT_PERIOD_90D: 90,
    REPORT_PERIOD_12M: 365,
}

EXPORT_FORMAT_PDF = "pdf"
EXPORT_FORMAT_EXCEL = "excel"
VALID_EXPORT_FORMATS = {EXPORT_FORMAT_PDF, EXPORT_FORMAT_EXCEL}

REPORT_TYPE_EXECUTIVE = "executive"
REPORT_TYPE_SALES = "sales"
REPORT_TYPE_PRODUCTION = "production"
REPORT_TYPE_INSTALLATION = "installation"
REPORT_TYPE_FINANCE = "finance"
VALID_REPORT_TYPES = {
    REPORT_TYPE_EXECUTIVE,
    REPORT_TYPE_SALES,
    REPORT_TYPE_PRODUCTION,
    REPORT_TYPE_INSTALLATION,
    REPORT_TYPE_FINANCE,
}


@dataclass(frozen=True)
class DateRange:
    date_from: date
    date_to: date


def resolve_date_range(
    *,
    period: str = DEFAULT_REPORT_PERIOD,
    date_from: date | None = None,
    date_to: date | None = None,
    today: date | None = None,
) -> DateRange:
    """Resolves a report's effective date range. An explicit `date_from`/`date_to`
    pair always wins (this is what "custom" means); otherwise falls back to a
    rolling window ending today, sized by `period`."""
    _today = today or date.today()
    if date_from is not None and date_to is not None:
        return DateRange(date_from=date_from, date_to=date_to)

    days = _PERIOD_DAYS.get(period, _PERIOD_DAYS[DEFAULT_REPORT_PERIOD])
    return DateRange(date_from=_today - timedelta(days=days), date_to=_today)
