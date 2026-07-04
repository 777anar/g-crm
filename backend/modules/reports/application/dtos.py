"""Application-layer input DTOs for the Reports module."""
import uuid
from dataclasses import dataclass

from modules.reports.domain.value_objects import DateRange


@dataclass(frozen=True)
class ReportFilterInput:
    company_id: uuid.UUID
    date_range: DateRange
