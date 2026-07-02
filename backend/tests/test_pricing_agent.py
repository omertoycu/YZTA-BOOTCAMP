def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "supersecret123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_listing(client, headers, **overrides):
    payload = {"title": "Test ilan", "district": "Kadikoy", "price": 15000, "room_count": "2+1"}
    payload.update(overrides)
    resp = client.post("/listings", json=payload, headers=headers)
    return resp.json()


def test_pricing_suggestion_reports_insufficient_data_with_few_comparables(client):
    headers = _register(client, "Ofis Pricing Test 1", "owner@pricing-test-1.com")
    listing = _create_listing(client, headers, title="Tek başına ilan")

    resp = client.get(f"/listings/{listing['id']}/pricing-suggestion", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_enough_data"] is False
    assert body["comparable_count"] == 0


def test_pricing_suggestion_returns_range_with_enough_comparables(client):
    headers = _register(client, "Ofis Pricing Test 2", "owner@pricing-test-2.com")
    for price in (14000, 15000, 16000):
        _create_listing(client, headers, title=f"Emsal {price}", price=price)
    target = _create_listing(client, headers, title="Değerlenecek ilan", price=0)

    resp = client.get(f"/listings/{target['id']}/pricing-suggestion", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_enough_data"] is True
    assert body["comparable_count"] >= 2
    assert body["suggested_min"] <= body["suggested_max"]


def test_pricing_suggestion_isolated_per_office(client):
    """Bir ofisin emsalleri başka bir ofisin fiyat önerisini etkilememeli (RLS
    ile tutarlı tenant izolasyonu ChromaDB metadata filtresiyle de korunmalı)."""
    headers_a = _register(client, "Ofis Pricing A", "ownerA@pricing-isolation.com")
    headers_b = _register(client, "Ofis Pricing B", "ownerB@pricing-isolation.com")

    for price in (14000, 15000, 16000):
        _create_listing(client, headers_a, title=f"A emsal {price}", price=price)
    listing_b = _create_listing(client, headers_b, title="B ilanı", price=15500)

    resp = client.get(f"/listings/{listing_b['id']}/pricing-suggestion", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json()["has_enough_data"] is False


def test_pricing_suggestion_unknown_listing_returns_404(client):
    headers = _register(client, "Ofis Pricing Test 3", "owner@pricing-test-3.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/listings/{fake_id}/pricing-suggestion", headers=headers)
    assert resp.status_code == 404
