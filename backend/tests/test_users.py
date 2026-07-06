def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "Supersecret123!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_my_profile_requires_auth(client):
    resp = client.get("/users/me")
    assert resp.status_code == 401


def test_get_my_profile_returns_email_and_role(client):
    """Profil sayfası için — kullanıcı hangi hesapla (e-posta) ve hangi rolle
    giriş yaptığını görebilmeli."""
    headers = _register(client, "Ofis Profil Test", "owner@profile-test.com")

    resp = client.get("/users/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "owner@profile-test.com"
    assert body["role"] == "owner"
    assert "created_at" in body


def test_get_my_profile_isolated_per_user(client):
    """Bir kullanıcı başka bir ofisin/kullanıcının profilini göremez — token
    sadece kendi user_id'sini taşıyor, RLS de office_id ile ek koruma sağlıyor."""
    headers_a = _register(client, "Ofis Profil A", "ownerA@profile-isolation.com")
    headers_b = _register(client, "Ofis Profil B", "ownerB@profile-isolation.com")

    resp_a = client.get("/users/me", headers=headers_a)
    resp_b = client.get("/users/me", headers=headers_b)
    assert resp_a.json()["email"] == "ownerA@profile-isolation.com"
    assert resp_b.json()["email"] == "ownerB@profile-isolation.com"
