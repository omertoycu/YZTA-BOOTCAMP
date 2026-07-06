def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "Supersecret123!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_listing(client, headers, **overrides):
    payload = {"title": "Test ilan", "district": "Kadikoy", "price": 15000, "room_count": "2+1"}
    payload.update(overrides)
    resp = client.post("/listings", json=payload, headers=headers)
    return resp.json()


def test_public_listing_returns_details_without_auth(client):
    headers = _register(client, "Ofis Public Test 1", "owner@public-test-1.com")
    listing = _create_listing(client, headers, title="Vitrin ilanı")

    resp = client.get(f"/public/listings/{listing['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Vitrin ilanı"
    assert body["office_name"] == "Ofis Public Test 1"
    assert body["district"] == "Kadikoy"


def test_public_listing_unknown_returns_404(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/public/listings/{fake_id}")
    assert resp.status_code == 404


def test_public_listing_view_recorded_and_visible_via_view_stats(client):
    headers = _register(client, "Ofis Public Test 2", "owner@public-test-2.com")
    listing = _create_listing(client, headers, title="Görüntülenen ilan")

    for _ in range(3):
        resp = client.get(f"/public/listings/{listing['id']}")
        assert resp.status_code == 200

    stats_resp = client.get(f"/listings/{listing['id']}/view-stats", headers=headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["view_count"] == 3
    assert stats["last_viewed_at"] is not None


def test_view_stats_zero_when_never_viewed(client):
    headers = _register(client, "Ofis Public Test 3", "owner@public-test-3.com")
    listing = _create_listing(client, headers, title="Hiç görüntülenmemiş ilan")

    resp = client.get(f"/listings/{listing['id']}/view-stats", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["view_count"] == 0
    assert body["last_viewed_at"] is None


def test_view_stats_unknown_listing_returns_404(client):
    headers = _register(client, "Ofis Public Test 4", "owner@public-test-4.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/listings/{fake_id}/view-stats", headers=headers)
    assert resp.status_code == 404


def test_view_stats_isolated_per_office(client):
    """Bir ofisin ilanının görüntülenme sayısını başka bir ofis göremez —
    /public/listings üzerinden atılan görüntülenme kaydı office_id taşır ve
    view-stats route'u normal tenant RLS'iyle (portfoyai_app) okur."""
    headers_a = _register(client, "Ofis Public A", "ownerA@public-isolation.com")
    headers_b = _register(client, "Ofis Public B", "ownerB@public-isolation.com")

    listing_a = _create_listing(client, headers_a, title="A ilanı")
    client.get(f"/public/listings/{listing_a['id']}")

    resp = client.get(f"/listings/{listing_a['id']}/view-stats", headers=headers_b)
    assert resp.status_code == 404
