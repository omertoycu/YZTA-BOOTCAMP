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


def test_get_listing_by_id(client):
    headers = _register(client, "Ofis Listing Test 3", "owner3@listing-test.com")
    create_resp = client.post(
        "/listings",
        json={"title": "1+1 Stüdyo", "district": "Sisli", "price": 12000, "room_count": "1+1"},
        headers=headers,
    )
    listing_id = create_resp.json()["id"]

    get_resp = client.get(f"/listings/{listing_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "1+1 Stüdyo"


def test_get_unknown_listing_returns_404(client):
    headers = _register(client, "Ofis Listing Test 4", "owner4@listing-test.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/listings/{fake_id}", headers=headers)
    assert resp.status_code == 404


def test_upload_photo_returns_503_when_s3_not_configured(client):
    """s3_endpoint_url ayarlanmamışken (henüz bucket kurulmadıysa) sert crash
    yerine anlamlı bir 503 dönmeli — geri kalan uygulama fotoğrafsız çalışmalı."""
    headers = _register(client, "Ofis Listing Test 5", "owner5@listing-test.com")
    create_resp = client.post(
        "/listings",
        json={"title": "Fotosuz ilan", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    listing_id = create_resp.json()["id"]

    resp = client.post(
        f"/listings/{listing_id}/photos",
        files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
        headers=headers,
    )
    assert resp.status_code == 503


def test_upload_photo_appends_url_to_listing(client, monkeypatch):
    from app.api.routes import listings as listings_route

    monkeypatch.setattr(listings_route, "upload_photo", lambda file_bytes, content_type, listing_id: "https://cdn.example.com/fake.jpg")

    headers = _register(client, "Ofis Listing Test 6", "owner6@listing-test.com")
    create_resp = client.post(
        "/listings",
        json={"title": "Fotoğraflı ilan", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    listing_id = create_resp.json()["id"]
    assert create_resp.json()["photos"] == []

    resp = client.post(
        f"/listings/{listing_id}/photos",
        files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["photos"] == ["https://cdn.example.com/fake.jpg"]


def test_upload_photo_unknown_listing_returns_404(client):
    headers = _register(client, "Ofis Listing Test 7", "owner7@listing-test.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.post(
        f"/listings/{fake_id}/photos",
        files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
        headers=headers,
    )
    assert resp.status_code == 404
