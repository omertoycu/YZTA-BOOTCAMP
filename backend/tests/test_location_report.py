from app.agents import location_report
from app.api.routes import listings as listings_route


def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "supersecret123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_listing(client, headers, title="Deniz manzaralı 3+1"):
    resp = client.post(
        "/listings",
        json={"title": title, "district": "Kadıköy", "price": 5_000_000, "room_count": "3+1"},
        headers=headers,
    )
    return resp.json()["id"]


def test_location_report_requires_auth(client):
    resp = client.post(
        "/listings/does-not-exist/location-report",
        json={"target_address": "Levent, İstanbul"},
    )
    assert resp.status_code == 401


def test_location_report_returns_404_for_missing_listing(client):
    headers = _register(client, "Ofis Location Test 1", "owner1@location-test.com")
    resp = client.post(
        "/listings/00000000-0000-0000-0000-000000000000/location-report",
        json={"target_address": "Levent, İstanbul"},
        headers=headers,
    )
    assert resp.status_code == 404


def test_location_report_returns_503_when_not_configured(client, monkeypatch):
    headers = _register(client, "Ofis Location Test 2", "owner2@location-test.com")
    listing_id = _create_listing(client, headers)

    def _raise(origin, destination):
        raise location_report.LocationReportError("__not_configured__")

    monkeypatch.setattr(listings_route, "get_travel_summary", _raise)

    resp = client.post(
        f"/listings/{listing_id}/location-report",
        json={"target_address": "Levent, İstanbul"},
        headers=headers,
    )
    assert resp.status_code == 503


def test_location_report_returns_pdf_on_success(client, monkeypatch):
    headers = _register(client, "Ofis Location Test 3", "owner3@location-test.com")
    listing_id = _create_listing(client, headers)

    def _fake_summary(origin, destination):
        return [
            {"mode": "driving", "label": "Araçla", "result": {"duration": "12 dakika", "distance": "5 km"}},
            {"mode": "walking", "label": "Yürüyerek", "result": None},
            {"mode": "transit", "label": "Toplu Taşıma ile", "result": {"duration": "20 dakika", "distance": "6 km"}},
        ]

    monkeypatch.setattr(listings_route, "get_travel_summary", _fake_summary)

    resp = client.post(
        f"/listings/{listing_id}/location-report",
        json={"target_address": "Levent, İstanbul", "target_label": "İş yeri"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"
