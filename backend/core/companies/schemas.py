import uuid
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    currency: str
    locale: str
    logo_url: Optional[str] = None
    enabled_modules: List[str]


class CompanyCreate(BaseModel):
    name: str
    slug: str
    currency: str = "AZN"
    locale: str = "en"
    logo_url: Optional[str] = None
    enabled_modules: List[str] = []
