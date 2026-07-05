from datetime import datetime, timedelta, timezone

from sqlalchemy import text


def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "supersecret123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_listing(client, headers, **overrides):
    payload = {"title": "Test ilan", "district": "Kadikoy", "price": 15000, "room_count": "2+1"}
    payload.update(overrides)
    resp = client.post("/listings", json=payload, headers=headers)
    return resp.json()


def _backdate(db_session, listing_id, days):
    then = datetime.now(timezone.utc) - timedelta(days=days)
    db_session.execute(
        text("UPDATE listings SET created_at = :created_at WHERE id = :id"),
        {"created_at": then, "id": listing_id},
    )
    db_session.commit()


def test_stale_alerts_ignores_recent_overpriced_listing(client):
    headers = _register(client, "Ofis Stale Test 1", "owner@stale-test-1.com")
    for price in (14000, 15000, 16000):
        _create_listing(client, headers, title=f"Emsal {price}", price=price)
    _create_listing(client, headers, title="Yeni ve pahalı ilan", price=50000)

    resp = client.get("/listings/stale-alerts", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_stale_alerts_flags_old_overpriced_listing(client, db_session):
    headers = _register(client, "Ofis Stale Test 2", "owner@stale-test-2.com")
    for price in (14000, 15000, 16000):
        _create_listing(client, headers, title=f"Emsal {price}", price=price)
    target = _create_listing(client, headers, title="Durgun ve pahalı ilan", price=50000)
    _backdate(db_session, target["id"], days=40)

    resp = client.get("/listings/stale-alerts", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["listing_id"] == target["id"]
    assert body[0]["age_days"] >= 30
    assert body[0]["overprice_pct"] > 0


def test_stale_alerts_ignores_old_but_fairly_priced_listing(client, db_session):
    headers = _register(client, "Ofis Stale Test 3", "owner@stale-test-3.com")
    for price in (14000, 15000, 16000):
        _create_listing(client, headers, title=f"Emsal {price}", price=price)
    target = _create_listing(client, headers, title="Durgun ama makul fiyatlı ilan", price=15200)
    _backdate(db_session, target["id"], days=40)

    resp = client.get("/listings/stale-alerts", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_stale_alerts_isolated_per_office(client, db_session):
    headers_a = _register(client, "Ofis Stale A", "ownerA@stale-isolation.com")
    headers_b = _register(client, "Ofis Stale B", "ownerB@stale-isolation.com")

    for price in (14000, 15000, 16000):
        _create_listing(client, headers_a, title=f"A emsal {price}", price=price)
    target_a = _create_listing(client, headers_a, title="A durgun ilan", price=50000)
    _backdate(db_session, target_a["id"], days=40)

    resp = client.get("/listings/stale-alerts", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json() == []
