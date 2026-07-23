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
    # `access_token`/`refresh_token` stay present in the body for backward
    # compatibility with Bearer-token API clients and the docs/Swagger "Try
    # it out" flow, but the browser frontend now authenticates via the
    # httpOnly cookies set alongside this response (see core/auth/router.py)
    # and no longer persists these fields anywhere -- see MASTER_DEVELOPMENT_ROADMAP.md
    # Phase 18. `role`/`module_permissions`/`active_company_id` are duplicated
    # here (they're also embedded in the access token's own claims) precisely
    # because the frontend can no longer read an httpOnly token's claims.
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    active_company_id: Optional[uuid.UUID] = None
    role: Optional[str] = None
    module_permissions: Dict[str, List[str]] = {}


class LoginResponse(TokenResponse):
    companies: List[CompanyMembership] = []
    # Set instead of issuing tokens when the user has MFA enabled (see
    # core/auth/mfa.py); the client must then call /auth/mfa/verify with
    # `mfa_token` + a TOTP code before it gets real tokens.
    mfa_required: bool = False
    mfa_token: Optional[str] = None


class SelectCompanyRequest(BaseModel):
    company_id: uuid.UUID


class RefreshRequest(BaseModel):
    # Optional because the browser frontend no longer holds the refresh
    # token in JS-readable storage -- it relies on the httpOnly refresh
    # cookie instead (see core/auth/router.py:refresh). Still accepted in
    # the body for Bearer-token API clients that manage their own tokens.
    refresh_token: Optional[str] = None


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    active_company_id: Optional[uuid.UUID]
    role: Optional[str]
    module_permissions: Dict[str, List[str]]
    mfa_enabled: bool


class MfaSetupOut(BaseModel):
    secret: str
    otpauth_uri: str


class MfaCodeRequest(BaseModel):
    code: str


class MfaVerifyRequest(BaseModel):
    mfa_token: str
    code: str
