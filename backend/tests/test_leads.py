def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "supersecret123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_match_returns_only_listings_matching_criteria(client):
    headers = _register(client, "Ofis Lead Test", "owner@lead-test.com")

    client.post(
        "/listings",
        json={"title": "Uygun ilan", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    client.post(
        "/listings",
        json={"title": "Bütçe dışı ilan", "district": "Kadikoy", "price": 50000, "room_count": "2+1"},
        headers=headers,
    )
    client.post(
        "/listings",
        json={"title": "Farklı bölge ilanı", "district": "Besiktas", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )

    lead_resp = client.post(
        "/leads",
        json={"contact_phone": "5551112233", "district": "Kadikoy", "room_count": "2+1", "budget_max": 20000},
        headers=headers,
    )
    assert lead_resp.status_code == 201
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    matched_titles = {m["title"] for m in match_resp.json()}
    assert matched_titles == {"Uygun ilan"}


def test_match_unknown_lead_returns_404(client):
    headers = _register(client, "Ofis Lead Test 2", "owner2@lead-test.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.post(f"/leads/{fake_id}/match", headers=headers)
    assert resp.status_code == 404
