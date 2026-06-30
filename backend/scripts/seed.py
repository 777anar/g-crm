"""Seeds the three companies and one owner user with access to all three,
per PROJECT_ANALYSIS.md / DATABASE_DESIGN.md. Idempotent: safe to re-run.

Usage: python scripts/seed.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from core.auth.models import ROLE_OWNER, User, UserCompanyRole
from core.auth.security import hash_password
from core.companies.models import Company
from core.db.session import SessionLocal

COMPANIES = [
    {"name": "G-STONE GALLERY", "slug": "g-stone-gallery", "enabled_modules": ["crm", "sales"]},
    {"name": "KORONA PREMIUM", "slug": "korona-premium", "enabled_modules": ["crm", "sales"]},
    {"name": "NEOLITH BAKU", "slug": "neolith-baku", "enabled_modules": ["crm", "sales"]},
]

OWNER_EMAIL = "owner@g-erp.example"
OWNER_PASSWORD = "ChangeMe123!"


def seed() -> None:
    db = SessionLocal()
    try:
        company_rows = []
        for spec in COMPANIES:
            existing = db.scalar(select(Company).where(Company.slug == spec["slug"]))
            if existing:
                company_rows.append(existing)
                continue
            company = Company(**spec)
            db.add(company)
            db.flush()
            company_rows.append(company)
            print(f"Created company: {company.name}")

        owner = db.scalar(select(User).where(User.email == OWNER_EMAIL))
        if owner is None:
            owner = User(email=OWNER_EMAIL, password_hash=hash_password(OWNER_PASSWORD), full_name="Platform Owner")
            db.add(owner)
            db.flush()
            print(f"Created owner user: {owner.email} (password: {OWNER_PASSWORD})")

        for company in company_rows:
            existing_role = db.scalar(
                select(UserCompanyRole).where(
                    UserCompanyRole.user_id == owner.id, UserCompanyRole.company_id == company.id
                )
            )
            if existing_role is None:
                db.add(UserCompanyRole(user_id=owner.id, company_id=company.id, role=ROLE_OWNER))
                print(f"Granted owner role on {company.name} to {owner.email}")

        db.commit()
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
