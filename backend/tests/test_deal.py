def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "supersecret123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_lead(client, headers, **overrides):
    payload = {"contact_phone": "5551234567"}
    payload.update(overrides)
    resp = client.post("/leads", json=payload, headers=headers)
    return resp.json()["id"]


def test_update_deal_sets_fields(client):
    headers = _register(client, "Ofis Deal Test 1", "owner@deal-test-1.com")
    lead_id = _create_lead(client, headers)

    resp = client.patch(
        f"/leads/{lead_id}/deal",
        json={
            "deal_amount": 5000000,
            "commission_amount": 100000,
            "deal_closed_at": "2026-07-01T12:00:00Z",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["deal_amount"] == 5000000
    assert body["commission_amount"] == 100000
    assert body["deal_closed_at"] is not None


def test_update_deal_clears_fields(client):
    headers = _register(client, "Ofis Deal Test 2", "owner@deal-test-2.com")
    lead_id = _create_lead(client, headers)
    client.patch(
        f"/leads/{lead_id}/deal",
        json={"deal_amount": 5000000, "commission_amount": 100000},
        headers=headers,
    )

    resp = client.patch(f"/leads/{lead_id}/deal", json={}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["deal_amount"] is None
    assert body["commission_amount"] is None


def test_update_deal_unknown_lead_returns_404(client):
    headers = _register(client, "Ofis Deal Test 3", "owner@deal-test-3.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.patch(
        f"/leads/{fake_id}/deal", json={"deal_amount": 1000}, headers=headers
    )
    assert resp.status_code == 404


def test_update_deal_requires_auth(client):
    headers = _register(client, "Ofis Deal Test 4", "owner@deal-test-4.com")
    lead_id = _create_lead(client, headers)
    resp = client.patch(f"/leads/{lead_id}/deal", json={"deal_amount": 1000})
    assert resp.status_code == 401
