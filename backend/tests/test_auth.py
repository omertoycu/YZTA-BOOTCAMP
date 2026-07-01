def test_register_and_login(client):
    register_resp = client.post(
        "/auth/register",
        json={
            "office_name": "Test Emlak Ofisi",
            "owner_email": "owner@test-office.com",
            "owner_password": "supersecret123",
        },
    )
    assert register_resp.status_code == 201
    assert "access_token" in register_resp.json()

    login_resp = client.post(
        "/auth/login",
        json={"email": "owner@test-office.com", "password": "supersecret123"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_login_with_wrong_password_fails(client):
    client.post(
        "/auth/register",
        json={
            "office_name": "Test Emlak Ofisi 2",
            "owner_email": "owner2@test-office.com",
            "owner_password": "supersecret123",
        },
    )
    resp = client.post(
        "/auth/login",
        json={"email": "owner2@test-office.com", "password": "wrong-password"},
    )
    assert resp.status_code == 401
