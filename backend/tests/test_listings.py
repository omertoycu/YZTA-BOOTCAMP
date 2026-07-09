def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "Supersecret123!"},
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


def test_create_listing_listing_type_defaults_to_sale(client):
    headers = _register(client, "Ofis Listing Test Type 1", "owner-type1@listing-test.com")
    resp = client.post(
        "/listings",
        json={"title": "Belirtilmemiş tip", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["listing_type"] == "sale"


def test_create_listing_accepts_rent_type(client):
    headers = _register(client, "Ofis Listing Test Type 2", "owner-type2@listing-test.com")
    resp = client.post(
        "/listings",
        json={
            "title": "Kiralık daire",
            "district": "Kadikoy",
            "price": 15000,
            "room_count": "2+1",
            "listing_type": "rent",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["listing_type"] == "rent"


def test_update_listing_type_switches_and_persists(client):
    """Migration 0020 mevcut portföyleri varsayılan "sale" işaretledi — gerçekte
    kiralık olanları danışman panelden düzeltebilmeli (gerçek ihtiyaç: kullanıcı
    "KİRALIK" başlıklı ama "Satılık" rozetli eski kayıtlar bildirdi)."""
    headers = _register(client, "Ofis Listing Type Patch", "owner-typepatch@listing-test.com")
    create_resp = client.post(
        "/listings",
        json={"title": "Yanlış tip kalmış kiralık", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    listing_id = create_resp.json()["id"]
    assert create_resp.json()["listing_type"] == "sale"

    patch_resp = client.patch(
        f"/listings/{listing_id}/type",
        json={"listing_type": "rent"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["listing_type"] == "rent"

    get_resp = client.get(f"/listings/{listing_id}", headers=headers)
    assert get_resp.json()["listing_type"] == "rent"


def test_update_listing_type_rejects_invalid_value(client):
    headers = _register(client, "Ofis Listing Type Patch 2", "owner-typepatch2@listing-test.com")
    create_resp = client.post(
        "/listings",
        json={"title": "Tip testi", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    listing_id = create_resp.json()["id"]

    resp = client.patch(f"/listings/{listing_id}/type", json={"listing_type": "lease"}, headers=headers)
    assert resp.status_code == 422


def test_create_listing_rejects_invalid_listing_type(client):
    headers = _register(client, "Ofis Listing Test Type 3", "owner-type3@listing-test.com")
    resp = client.post(
        "/listings",
        json={
            "title": "Geçersiz tip",
            "district": "Kadikoy",
            "price": 15000,
            "room_count": "2+1",
            "listing_type": "lease",
        },
        headers=headers,
    )
    assert resp.status_code == 422


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


def test_upload_photo_appends_proxy_url_to_listing(client, monkeypatch):
    """upload_photo artık bare bir S3 key döner (bucket private olduğu için tam
    URL değil); API yanıtı bu key'i backend proxy route'una (GET /listings/photos/{key})
    işaret eden bir URL'e çevirmeli — bkz. app/schemas/listing.py."""
    from app.api.routes import listings as listings_route

    fake_key = "listings/fake-listing-id/fake.jpg"
    monkeypatch.setattr(listings_route, "upload_photo", lambda file_bytes, content_type, listing_id: fake_key)

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
    assert resp.json()["photos"] == [f"http://localhost:8010/listings/photos/{fake_key}"]


def test_get_listing_photo_streams_bytes(client, monkeypatch):
    from app.api.routes import listings as listings_route

    monkeypatch.setattr(
        listings_route, "fetch_photo", lambda key: (b"fake-image-bytes", "image/jpeg")
    )

    resp = client.get("/listings/photos/listings/some-id/fake.jpg")
    assert resp.status_code == 200
    assert resp.content == b"fake-image-bytes"
    assert resp.headers["content-type"] == "image/jpeg"


def test_get_listing_photo_returns_503_when_s3_not_configured(client):
    resp = client.get("/listings/photos/listings/some-id/missing.jpg")
    assert resp.status_code == 503


def test_upload_photo_unknown_listing_returns_404(client):
    headers = _register(client, "Ofis Listing Test 7", "owner7@listing-test.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.post(
        f"/listings/{fake_id}/photos",
        files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
        headers=headers,
    )
    assert resp.status_code == 404


def test_update_listing_patches_only_given_fields(client):
    headers = _register(client, "Ofis Listing Edit 1", "owner-edit1@listing-test.com")
    create_resp = client.post(
        "/listings",
        json={"title": "Eski başlık", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    listing_id = create_resp.json()["id"]

    patch_resp = client.patch(
        f"/listings/{listing_id}",
        json={"price": 20000},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert body["price"] == 20000
    # dokunulmayan alanlar aynı kalmalı
    assert body["title"] == "Eski başlık"
    assert body["district"] == "Kadikoy"


def test_update_listing_can_change_title_and_location(client):
    headers = _register(client, "Ofis Listing Edit 2", "owner-edit2@listing-test.com")
    create_resp = client.post(
        "/listings",
        json={"title": "Eski başlık", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    listing_id = create_resp.json()["id"]

    patch_resp = client.patch(
        f"/listings/{listing_id}",
        json={"title": "Yeni başlık", "district": "Uskudar", "room_count": "3+1", "square_meters": 120},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert body["title"] == "Yeni başlık"
    assert body["district"] == "Uskudar"
    assert body["room_count"] == "3+1"
    assert body["square_meters"] == 120


def test_update_listing_rejects_empty_title(client):
    headers = _register(client, "Ofis Listing Edit 3", "owner-edit3@listing-test.com")
    create_resp = client.post(
        "/listings",
        json={"title": "Başlık", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    listing_id = create_resp.json()["id"]

    resp = client.patch(f"/listings/{listing_id}", json={"title": "   "}, headers=headers)
    assert resp.status_code == 422


def test_update_listing_rejects_non_positive_price(client):
    headers = _register(client, "Ofis Listing Edit 4", "owner-edit4@listing-test.com")
    create_resp = client.post(
        "/listings",
        json={"title": "Başlık", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    listing_id = create_resp.json()["id"]

    resp = client.patch(f"/listings/{listing_id}", json={"price": 0}, headers=headers)
    assert resp.status_code == 422


def test_update_unknown_listing_returns_404(client):
    headers = _register(client, "Ofis Listing Edit 5", "owner-edit5@listing-test.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.patch(f"/listings/{fake_id}", json={"price": 10000}, headers=headers)
    assert resp.status_code == 404


def test_update_listing_requires_auth(client):
    resp = client.patch("/listings/does-not-exist", json={"price": 10000})
    assert resp.status_code == 401


def test_delete_listing_photo_removes_from_list(client, monkeypatch):
    from app.api.routes import listings as listings_route

    fake_keys = iter(["listings/fake/one.jpg", "listings/fake/two.jpg"])
    monkeypatch.setattr(
        listings_route, "upload_photo", lambda file_bytes, content_type, listing_id: next(fake_keys)
    )
    deleted_keys = []
    monkeypatch.setattr(listings_route, "delete_photo", lambda key: deleted_keys.append(key))

    headers = _register(client, "Ofis Listing Photo Delete 1", "owner-photodel1@listing-test.com")
    create_resp = client.post(
        "/listings",
        json={"title": "Fotoğraflı ilan", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    listing_id = create_resp.json()["id"]

    for _ in range(2):
        upload_resp = client.post(
            f"/listings/{listing_id}/photos",
            files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
            headers=headers,
        )
        assert upload_resp.status_code == 200
    assert len(upload_resp.json()["photos"]) == 2

    delete_resp = client.delete(f"/listings/{listing_id}/photos/0", headers=headers)
    assert delete_resp.status_code == 200
    assert len(delete_resp.json()["photos"]) == 1
    assert deleted_keys == ["listings/fake/one.jpg"]


def test_delete_listing_photo_out_of_range_returns_404(client):
    headers = _register(client, "Ofis Listing Photo Delete 2", "owner-photodel2@listing-test.com")
    create_resp = client.post(
        "/listings",
        json={"title": "Fotosuz ilan", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    listing_id = create_resp.json()["id"]

    resp = client.delete(f"/listings/{listing_id}/photos/0", headers=headers)
    assert resp.status_code == 404


def test_delete_listing_photo_unknown_listing_returns_404(client):
    headers = _register(client, "Ofis Listing Photo Delete 3", "owner-photodel3@listing-test.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.delete(f"/listings/{fake_id}/photos/0", headers=headers)
    assert resp.status_code == 404


class _FakeImageResponse:
    def __init__(self, content: bytes, content_type: str = "image/jpeg"):
        self.content = content
        self.headers = {"content-type": content_type}

    def raise_for_status(self):
        pass


class _FakeImageHttpClient:
    def __init__(self, response):
        self._response = response

    def get(self, url):
        return self._response

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_photo_from_url_rejects_unsupported_host(client):
    """SSRF önlemi: sadece Sahibinden'in görsel CDN'ine (shbdn.com) izin
    verilir — rastgele bir host'a sunucudan istek attırılamamalı."""
    headers = _register(client, "Ofis Listing Test 8", "owner8@listing-test.com")
    create_resp = client.post(
        "/listings",
        json={"title": "Kapak fotoğraflı ilan", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    listing_id = create_resp.json()["id"]

    resp = client.post(
        f"/listings/{listing_id}/photos/from-url",
        json={"url": "https://evil-internal-service.example.com/steal"},
        headers=headers,
    )
    assert resp.status_code == 400


def test_photo_from_url_unknown_listing_returns_404(client):
    headers = _register(client, "Ofis Listing Test 9", "owner9@listing-test.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.post(
        f"/listings/{fake_id}/photos/from-url",
        json={"url": "https://i0.shbdn.com/a.jpg"},
        headers=headers,
    )
    assert resp.status_code == 404


def test_photo_from_url_downloads_and_appends_proxy_url(client, monkeypatch):
    """Bulk aktarımdan gelen kapak fotoğrafı URL'i sunucu tarafında indirilip
    (CORS'a takılmadan) kendi depomuza yüklenmeli — avif dahil (Sahibinden CDN'i
    bazı fotoğrafları avif olarak sunuyor, curl ile doğrulandı)."""
    from app.api.routes import listings as listings_route

    fake_key = "listings/fake-listing-id/fake.avif"
    monkeypatch.setattr(listings_route, "upload_photo", lambda file_bytes, content_type, listing_id: fake_key)
    monkeypatch.setattr(
        listings_route,
        "get_http_client",
        lambda: _FakeImageHttpClient(_FakeImageResponse(b"fake-avif-bytes", "image/avif")),
    )

    headers = _register(client, "Ofis Listing Test 10", "owner10@listing-test.com")
    create_resp = client.post(
        "/listings",
        json={"title": "Kapak fotoğraflı ilan 2", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    listing_id = create_resp.json()["id"]

    resp = client.post(
        f"/listings/{listing_id}/photos/from-url",
        json={"url": "https://i0.shbdn.com/photos/a.avif"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["photos"] == [f"http://localhost:8010/listings/photos/{fake_key}"]


def test_photo_from_url_returns_502_on_fetch_failure(client, monkeypatch):
    import httpx

    from app.api.routes import listings as listings_route

    class _FailingClient:
        def get(self, url):
            raise httpx.ConnectError("boom")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(listings_route, "get_http_client", lambda: _FailingClient())

    headers = _register(client, "Ofis Listing Test 11", "owner11@listing-test.com")
    create_resp = client.post(
        "/listings",
        json={"title": "Kapak indirilemeyen ilan", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    listing_id = create_resp.json()["id"]

    resp = client.post(
        f"/listings/{listing_id}/photos/from-url",
        json={"url": "https://i0.shbdn.com/photos/a.jpg"},
        headers=headers,
    )
    assert resp.status_code == 502
