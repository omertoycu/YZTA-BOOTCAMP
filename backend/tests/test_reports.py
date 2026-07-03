def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "supersecret123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_overview_requires_auth(client):
    resp = client.get("/reports/overview")
    assert resp.status_code == 401


def test_overview_returns_zeroes_for_empty_office(client):
    headers = _register(client, "Ofis Reports Test 1", "owner1@reports-test.com")
    resp = client.get("/reports/overview", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["listing_count"] == 0
    assert body["lead_count"] == 0
    assert body["average_score"] is None
    assert len(body["score_distribution"]) == 3
    assert all(bucket["count"] == 0 for bucket in body["score_distribution"])


def test_overview_aggregates_listings_and_leads(client):
    headers = _register(client, "Ofis Reports Test 2", "owner2@reports-test.com")

    client.post(
        "/listings",
        json={"title": "Deniz manzaralı 3+1", "district": "Kadıköy", "price": 5_000_000, "room_count": "3+1"},
        headers=headers,
    )
    client.post(
        "/listings",
        json={"title": "Merkezi 2+1", "district": "Kadıköy", "price": 3_000_000, "room_count": "2+1"},
        headers=headers,
    )

    lead_resp = client.post(
        "/leads",
        json={"contact_phone": "905551112233", "district": "Kadıköy", "budget_max": 4_000_000},
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]
    client.post(f"/leads/{lead_id}/score", headers=headers)

    resp = client.get("/reports/overview", headers=headers)
    assert resp.status_code == 200
    body = resp.json()

    assert body["listing_count"] == 2
    assert body["active_listing_count"] == 2
    assert body["listings_by_district"] == [{"district": "Kadıköy", "count": 2}]

    assert body["lead_count"] == 1
    assert body["leads_by_source"] == {"manual": 1}
    assert body["leads_by_district"] == [{"district": "Kadıköy", "count": 1}]

    assert body["scored_lead_count"] == 1
    assert body["average_score"] is not None


def test_overview_is_tenant_scoped(client):
    headers_a = _register(client, "Ofis Reports Test 3A", "owner3a@reports-test.com")
    headers_b = _register(client, "Ofis Reports Test 3B", "owner3b@reports-test.com")

    client.post(
        "/listings",
        json={"title": "Sadece A ofisinin ilanı", "district": "Beşiktaş", "price": 1_000_000, "room_count": "1+1"},
        headers=headers_a,
    )

    resp_b = client.get("/reports/overview", headers=headers_b)
    assert resp_b.status_code == 200
    assert resp_b.json()["listing_count"] == 0
