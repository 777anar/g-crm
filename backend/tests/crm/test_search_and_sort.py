"""Business Optimization Phase: faster data entry for daily CRM use requires
findable records -- covers the new ?search= and ?sort= list parameters for
Customers and Leads."""


def test_search_customers_by_name(app_client, owner_headers):
    app_client.post("/api/v1/crm/customers", headers=owner_headers, json={"name": "Rashad Aliyev", "type": "individual"})
    app_client.post("/api/v1/crm/customers", headers=owner_headers, json={"name": "Leyla Huseynova", "type": "individual"})

    response = app_client.get("/api/v1/crm/customers", headers=owner_headers, params={"search": "Rashad"})
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Rashad Aliyev"


def test_search_customers_by_phone(app_client, owner_headers):
    app_client.post(
        "/api/v1/crm/customers",
        headers=owner_headers,
        json={"name": "Phone Match Co", "type": "business", "phone": "+994501234567"},
    )
    app_client.post("/api/v1/crm/customers", headers=owner_headers, json={"name": "No Phone Co", "type": "business"})

    response = app_client.get("/api/v1/crm/customers", headers=owner_headers, params={"search": "501234567"})
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Phone Match Co"


def test_search_customers_by_company_name(app_client, owner_headers):
    app_client.post(
        "/api/v1/crm/customers",
        headers=owner_headers,
        json={"name": "Person A", "type": "individual", "company_name": "Aliyev Holding"},
    )
    response = app_client.get("/api/v1/crm/customers", headers=owner_headers, params={"search": "Aliyev Holding"})
    items = response.json()["items"]
    assert len(items) == 1


def test_search_customers_is_case_insensitive(app_client, owner_headers):
    app_client.post("/api/v1/crm/customers", headers=owner_headers, json={"name": "CamelCase Co", "type": "business"})
    response = app_client.get("/api/v1/crm/customers", headers=owner_headers, params={"search": "camelcase"})
    assert len(response.json()["items"]) == 1


def test_search_customers_no_match_returns_empty(app_client, owner_headers):
    app_client.post("/api/v1/crm/customers", headers=owner_headers, json={"name": "Real Co", "type": "business"})
    response = app_client.get("/api/v1/crm/customers", headers=owner_headers, params={"search": "nonexistent-xyz"})
    assert response.json()["items"] == []


def test_sort_customers_by_name_ascending(app_client, owner_headers):
    for name in ["Charlie Co", "Alpha Co", "Bravo Co"]:
        app_client.post("/api/v1/crm/customers", headers=owner_headers, json={"name": name, "type": "business"})

    response = app_client.get("/api/v1/crm/customers", headers=owner_headers, params={"sort": "name"})
    names = [c["name"] for c in response.json()["items"]]
    assert names == sorted(names)


def test_sort_customers_by_name_descending(app_client, owner_headers):
    for name in ["Charlie Co", "Alpha Co", "Bravo Co"]:
        app_client.post("/api/v1/crm/customers", headers=owner_headers, json={"name": name, "type": "business"})

    response = app_client.get("/api/v1/crm/customers", headers=owner_headers, params={"sort": "-name"})
    names = [c["name"] for c in response.json()["items"]]
    assert names == sorted(names, reverse=True)


def test_sort_customers_falls_back_to_created_at_for_unknown_field(app_client, owner_headers):
    app_client.post("/api/v1/crm/customers", headers=owner_headers, json={"name": "Fallback Co", "type": "business"})
    response = app_client.get("/api/v1/crm/customers", headers=owner_headers, params={"sort": "secret_column"})
    assert response.status_code == 200


def test_search_leads_by_name(app_client, owner_headers):
    app_client.post("/api/v1/crm/leads", headers=owner_headers, json={"full_name": "Tural Quliyev", "source_channel": "website"})
    app_client.post("/api/v1/crm/leads", headers=owner_headers, json={"full_name": "Nigar Mammadova", "source_channel": "website"})

    response = app_client.get("/api/v1/crm/leads", headers=owner_headers, params={"search": "Tural"})
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["full_name"] == "Tural Quliyev"


def test_sort_leads_by_name(app_client, owner_headers):
    for name in ["Zeynab", "Amina"]:
        app_client.post("/api/v1/crm/leads", headers=owner_headers, json={"full_name": name, "source_channel": "website"})

    response = app_client.get("/api/v1/crm/leads", headers=owner_headers, params={"sort": "full_name"})
    names = [lead["full_name"] for lead in response.json()["items"]]
    assert names == sorted(names)
