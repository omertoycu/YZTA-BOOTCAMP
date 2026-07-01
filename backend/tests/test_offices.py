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
