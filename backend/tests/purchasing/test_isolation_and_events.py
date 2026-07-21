"""Multi-company isolation and audit/event verification for the Purchasing
module -- per the requirement that "everything must be multi-company", and
per the established pattern of recording an audit entry + domain event for
every write action."""


def test_purchase_orders_are_isolated_by_company(app_client, db_session, owner_headers, supplier, material):
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    po = app_client.post(
        "/api/v1/purchasing/purchase-orders",
        headers=owner_headers,
        json={
            "supplier_id": supplier["id"],
            "lines": [{"material_id": str(material.id), "description": "X", "quantity": "1", "unit_cost": "10"}],
        },
    ).json()

    other_company = Company(
        name="KORONA PREMIUM", slug="korona-premium-purchasing-test", enabled_modules=["purchasing"]
    )
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="other-owner@purchasing.test", password_hash=hash_password("x"), full_name="Other Owner")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_token = create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    response = app_client.get(f"/api/v1/purchasing/purchase-orders/{po['id']}", headers=other_headers)
    assert response.status_code == 404

    other_supplier_list = app_client.get("/api/v1/purchasing/suppliers", headers=other_headers).json()
    assert supplier["id"] not in [s["id"] for s in other_supplier_list["items"]]

    other_po_list = app_client.get("/api/v1/purchasing/purchase-orders", headers=other_headers).json()
    assert po["id"] not in [p["id"] for p in other_po_list["items"]]


def test_po_numbers_can_repeat_across_companies(app_client, db_session, owner_headers, supplier, material):
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    first = app_client.post(
        "/api/v1/purchasing/purchase-orders",
        headers=owner_headers,
        json={
            "supplier_id": supplier["id"],
            "lines": [{"material_id": str(material.id), "description": "X", "quantity": "1", "unit_cost": "10"}],
        },
    ).json()
    assert first["po_number"].endswith("-0001")

    other_company = Company(
        name="KORONA PREMIUM", slug="korona-premium-purchasing-seq-test", enabled_modules=["purchasing"]
    )
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="other-owner-2@purchasing.test", password_hash=hash_password("x"), full_name="Other Owner 2")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_token = create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    other_supplier = app_client.post(
        "/api/v1/purchasing/suppliers", headers=other_headers, json={"name": "Other Supplier"}
    ).json()
    other_po = app_client.post(
        "/api/v1/purchasing/purchase-orders",
        headers=other_headers,
        json={"supplier_id": other_supplier["id"], "lines": [{"description": "X", "quantity": "1", "unit_cost": "10"}]},
    ).json()
    assert other_po["po_number"].endswith("-0001")
    assert other_po["po_number"] == first["po_number"]


def test_supplier_creation_writes_audit_and_event(app_client, owner_headers, db_session, owner_user, company):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    app_client.post("/api/v1/purchasing/suppliers", headers=owner_headers, json={"name": "Antolini"})

    entry = db_session.query(AuditLog).filter(AuditLog.action == "supplier.created").first()
    assert entry is not None
    assert entry.actor_user_id == owner_user.id
    assert entry.company_id == company.id
    assert entry.module == "purchasing"

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "SupplierCreated" in events


def test_purchase_order_creation_writes_audit_and_event(app_client, owner_headers, db_session, company, supplier, material):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    app_client.post(
        "/api/v1/purchasing/purchase-orders",
        headers=owner_headers,
        json={
            "supplier_id": supplier["id"],
            "lines": [{"material_id": str(material.id), "description": "X", "quantity": "1", "unit_cost": "10"}],
        },
    )

    entry = db_session.query(AuditLog).filter(AuditLog.action == "purchase_order.created").first()
    assert entry is not None
    assert entry.company_id == company.id
    assert entry.module == "purchasing"

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "PurchaseOrderCreated" in events


def test_receiving_writes_audit_and_publishes_events(app_client, owner_headers, db_session, confirmed_po):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    line_id = app_client.get(
        f"/api/v1/purchasing/purchase-orders/{confirmed_po['id']}/lines", headers=owner_headers
    ).json()["items"][0]["id"]

    app_client.post(
        f"/api/v1/purchasing/purchase-orders/{confirmed_po['id']}/lines/{line_id}/receive",
        headers=owner_headers,
        json={"quantity_received": "10"},
    )

    actions = [
        r.action for r in db_session.query(AuditLog).filter(AuditLog.entity_type == "purchase_order_line").all()
    ]
    assert "purchase_order.line_received" in actions

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "PurchaseOrderLineReceived" in events
    assert "PurchaseOrderStatusChanged" in events  # confirmed -> received, since the only line was fully received
