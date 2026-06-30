"""Multi-company isolation and audit/event verification for the Stone
Catalog module -- per the requirement that "everything must be
multi-company", and per the established pattern of recording an audit
entry + domain event for every write action."""


def test_brands_are_isolated_by_company(app_client, db_session, owner_headers, company):
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    other_company = Company(name="KORONA PREMIUM", slug="korona-premium-catalog-test", enabled_modules=["catalog"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="other-owner@catalog.test", password_hash=hash_password("x"), full_name="Other Owner")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_token = create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    created = app_client.post("/api/v1/catalog/brands", headers=owner_headers, json={"name": "Isolated Brand"}).json()

    response = app_client.get(f"/api/v1/catalog/brands/{created['id']}", headers=other_headers)
    assert response.status_code == 404

    other_company_brands = app_client.get("/api/v1/catalog/brands", headers=other_headers).json()
    assert created["id"] not in [b["id"] for b in other_company_brands["items"]]


def test_materials_are_isolated_by_company(app_client, db_session, owner_headers, company):
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    brand = app_client.post("/api/v1/catalog/brands", headers=owner_headers, json={"name": "NEOLITH"}).json()
    material = app_client.post(
        "/api/v1/catalog/materials", headers=owner_headers, json={"brand_id": brand["id"], "name": "Calacatta"}
    ).json()

    other_company = Company(name="NEOLITH BAKU", slug="neolith-baku-catalog-test", enabled_modules=["catalog"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="other-owner-2@catalog.test", password_hash=hash_password("x"), full_name="Other Owner 2")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_token = create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    response = app_client.get(f"/api/v1/catalog/materials/{material['id']}", headers=other_headers)
    assert response.status_code == 404


def test_slab_numbers_can_repeat_across_companies(app_client, db_session, owner_headers, company):
    """The unique-slab-number constraint is scoped per company -- two
    different companies may both use "SL-0001" without conflict."""
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    brand = app_client.post("/api/v1/catalog/brands", headers=owner_headers, json={"name": "NEOLITH"}).json()
    material = app_client.post(
        "/api/v1/catalog/materials", headers=owner_headers, json={"brand_id": brand["id"], "name": "Calacatta"}
    ).json()
    warehouse = app_client.post(
        "/api/v1/catalog/warehouses", headers=owner_headers, json={"name": "Main Warehouse"}
    ).json()
    first = app_client.post(
        "/api/v1/catalog/slabs",
        headers=owner_headers,
        json={"material_id": material["id"], "warehouse_id": warehouse["id"], "slab_number": "SL-SHARED"},
    )
    assert first.status_code == 200

    other_company = Company(name="KORONA PREMIUM", slug="korona-premium-slab-test", enabled_modules=["catalog"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="other-owner-3@catalog.test", password_hash=hash_password("x"), full_name="Other Owner 3")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_token = create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    other_brand = app_client.post("/api/v1/catalog/brands", headers=other_headers, json={"name": "NEOLITH"}).json()
    other_material = app_client.post(
        "/api/v1/catalog/materials", headers=other_headers, json={"brand_id": other_brand["id"], "name": "Calacatta"}
    ).json()
    other_warehouse = app_client.post(
        "/api/v1/catalog/warehouses", headers=other_headers, json={"name": "Other Warehouse"}
    ).json()

    second = app_client.post(
        "/api/v1/catalog/slabs",
        headers=other_headers,
        json={"material_id": other_material["id"], "warehouse_id": other_warehouse["id"], "slab_number": "SL-SHARED"},
    )
    assert second.status_code == 200


def test_brand_creation_writes_audit_and_event(app_client, owner_headers, db_session, owner_user, company):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    app_client.post("/api/v1/catalog/brands", headers=owner_headers, json={"name": "Audit Brand"})

    entry = db_session.query(AuditLog).filter(AuditLog.action == "brand.created").first()
    assert entry is not None
    assert entry.actor_user_id == owner_user.id
    assert entry.company_id == company.id
    assert entry.module == "catalog"

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "BrandCreated" in events


def test_slab_status_change_writes_audit_and_event(app_client, owner_headers, db_session):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    brand = app_client.post("/api/v1/catalog/brands", headers=owner_headers, json={"name": "NEOLITH"}).json()
    material = app_client.post(
        "/api/v1/catalog/materials", headers=owner_headers, json={"brand_id": brand["id"], "name": "Calacatta"}
    ).json()
    warehouse = app_client.post(
        "/api/v1/catalog/warehouses", headers=owner_headers, json={"name": "Main Warehouse"}
    ).json()
    slab = app_client.post(
        "/api/v1/catalog/slabs",
        headers=owner_headers,
        json={"material_id": material["id"], "warehouse_id": warehouse["id"], "slab_number": "SL-EVT"},
    ).json()

    app_client.patch(f"/api/v1/catalog/slabs/{slab['id']}/status", headers=owner_headers, json={"status": "reserved"})

    actions = [r.action for r in db_session.query(AuditLog).filter(AuditLog.entity_type == "slab").all()]
    assert "slab.status_changed" in actions

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "SlabStatusChanged" in events
    assert "SlabCreated" in events
