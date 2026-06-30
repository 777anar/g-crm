import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr


class CompanyMembership(BaseModel):
    id: uuid.UUID
    name: str
    role: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class LoginResponse(TokenResponse):
    companies: List[CompanyMembership]


class SelectCompanyRequest(BaseModel):
    company_id: uuid.UUID


class RefreshRequest(BaseModel):
    refresh_token: str


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    active_company_id: Optional[uuid.UUID]
    role: Optional[str]
    module_permissions: Dict[str, List[str]]
