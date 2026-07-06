def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "Supersecret123!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_my_office_returns_own_office(client):
    headers = _register(client, "Ofis Me Test", "owner@office-me-test.com")
    resp = client.get("/offices/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Ofis Me Test"
    assert body["subscription_plan"] == "starter"


def test_get_my_office_requires_auth(client):
    resp = client.get("/offices/me")
    assert resp.status_code == 401


def test_update_notification_phone(client):
    headers = _register(client, "Ofis Notify Test 1", "owner@office-notify-test.com")

    resp = client.patch("/offices/me", json={"notification_phone": "905551234567"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["notification_phone"] == "905551234567"

    resp = client.get("/offices/me", headers=headers)
    assert resp.json()["notification_phone"] == "905551234567"


def test_clear_notification_phone(client):
    headers = _register(client, "Ofis Notify Test 2", "owner@office-notify-test-2.com")
    client.patch("/offices/me", json={"notification_phone": "905551234567"}, headers=headers)

    resp = client.patch("/offices/me", json={"notification_phone": None}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["notification_phone"] is None


def test_update_office_requires_auth(client):
    resp = client.patch("/offices/me", json={"notification_phone": "905551234567"})
    assert resp.status_code == 401


def test_update_whatsapp_phone_number_id(client):
    headers = _register(client, "Ofis WA Test 1", "owner@office-wa-test-1.com")

    resp = client.patch(
        "/offices/me", json={"whatsapp_phone_number_id": "1279529618577191"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["whatsapp_phone_number_id"] == "1279529618577191"


def test_updating_one_field_does_not_clear_the_other(client):
    """exclude_unset regresyon testi: notification_phone'u ayrıca güncellemek
    daha önce set edilmiş whatsapp_phone_number_id'yi sıfırlamamalı (ve tersi)."""
    headers = _register(client, "Ofis WA Test 2", "owner@office-wa-test-2.com")

    client.patch("/offices/me", json={"whatsapp_phone_number_id": "2000000000000002"}, headers=headers)
    resp = client.patch("/offices/me", json={"notification_phone": "905551234567"}, headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["notification_phone"] == "905551234567"
    assert body["whatsapp_phone_number_id"] == "2000000000000002"


def test_duplicate_whatsapp_phone_number_id_returns_409(client):
    headers_a = _register(client, "Ofis WA Test 3A", "ownerA@office-wa-test-3.com")
    headers_b = _register(client, "Ofis WA Test 3B", "ownerB@office-wa-test-3.com")

    resp_a = client.patch("/offices/me", json={"whatsapp_phone_number_id": "3000000000000003"}, headers=headers_a)
    assert resp_a.status_code == 200
    resp = client.patch(
        "/offices/me", json={"whatsapp_phone_number_id": "3000000000000003"}, headers=headers_b
    )
    assert resp.status_code == 409


def test_upload_logo_returns_503_when_s3_not_configured(client):
    headers = _register(client, "Ofis Logo Test 1", "owner@office-logo-test-1.com")
    resp = client.post(
        "/offices/me/logo",
        files={"file": ("logo.png", b"fake-logo-bytes", "image/png")},
        headers=headers,
    )
    assert resp.status_code == 503


def test_upload_logo_sets_logo_url(client, monkeypatch):
    """Logo yüklenince OfficeResponse.logo_url proxy route'una işaret eden bir
    URL dönmeli (listings.photos ile aynı desen — bucket private)."""
    from app.api.routes import offices as offices_route

    fake_key = "offices/fake-office-id/logo-abc.png"
    monkeypatch.setattr(
        offices_route, "upload_office_logo", lambda file_bytes, content_type, office_id: fake_key
    )

    headers = _register(client, "Ofis Logo Test 2", "owner@office-logo-test-2.com")
    resp = client.post(
        "/offices/me/logo",
        files={"file": ("logo.png", b"fake-logo-bytes", "image/png")},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["logo_url"] == f"http://localhost:8010/offices/logo/{fake_key}"

    # GET /offices/me de aynı logo_url'i dönmeli.
    me = client.get("/offices/me", headers=headers)
    assert me.json()["logo_url"] == f"http://localhost:8010/offices/logo/{fake_key}"


def test_get_office_logo_streams_bytes(client, monkeypatch):
    from app.api.routes import offices as offices_route

    monkeypatch.setattr(offices_route, "fetch_photo", lambda key: (b"fake-logo-bytes", "image/png"))

    resp = client.get("/offices/logo/offices/some-office/logo-abc.png")
    assert resp.status_code == 200
    assert resp.content == b"fake-logo-bytes"
    assert resp.headers["content-type"] == "image/png"


def test_get_office_logo_rejects_non_office_keys(client):
    """Logo proxy'si sadece offices/ önekli anahtarları sunmalı — ilan
    fotoğrafları gibi başka nesnelerin auth'suz sızması engellenmeli."""
    resp = client.get("/offices/logo/listings/some-listing/photo.jpg")
    assert resp.status_code == 404
