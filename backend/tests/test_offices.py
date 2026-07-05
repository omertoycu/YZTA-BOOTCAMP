def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "supersecret123"},
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
