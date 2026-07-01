def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "supersecret123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_listing_requires_auth(client):
    resp = client.post(
        "/listings",
        json={"title": "Test", "district": "Kadikoy", "price": 10000, "room_count": "1+1"},
    )
    assert resp.status_code == 401


def test_create_listing_rejects_missing_fields(client):
    headers = _register(client, "Ofis Listing Test", "owner@listing-test.com")
    resp = client.post("/listings", json={"title": "Eksik ilan"}, headers=headers)
    assert resp.status_code == 422


def test_create_and_list_listing(client):
    headers = _register(client, "Ofis Listing Test 2", "owner2@listing-test.com")
    create_resp = client.post(
        "/listings",
        json={"title": "3+1 Daire", "district": "Uskudar", "price": 25000, "room_count": "3+1"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["title"] == "3+1 Daire"
    assert body["status"] == "active"
    assert body["created_at"] is not None

    list_resp = client.get("/listings", headers=headers)
    assert list_resp.status_code == 200
    titles = {listing["title"] for listing in list_resp.json()}
    assert "3+1 Daire" in titles
