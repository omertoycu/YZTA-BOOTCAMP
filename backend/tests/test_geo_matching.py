import uuid

from app.agents import geocoding, matching

FAKE_COORDS = {
    "kadikoy": (40.9833, 29.0333),
    "uskudar": (41.0225, 29.0244),  # Kadıköy'e ~5km yakın
    "sisli": (41.5000, 29.9000),  # Kadıköy'den ~90km uzak (test amaçlı abartılı)
}


def _fake_geocode(db, district):
    if not district:
        return None
    return FAKE_COORDS.get(district.strip().lower())


def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "supersecret123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_radius_match_includes_nearby_excludes_far(client, monkeypatch):
    monkeypatch.setattr(matching, "geocode_district", _fake_geocode)

    headers = _register(client, "Ofis Geo Test 1", "owner1@geo-test.com")
    client.post(
        "/listings",
        json={"title": "Yakın ilan", "district": "Uskudar", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    client.post(
        "/listings",
        json={"title": "Uzak ilan", "district": "Sisli", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )

    lead_resp = client.post(
        "/leads",
        json={"contact_phone": "5551112233", "district": "Kadikoy", "radius_km": 10},
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    titles = {m["title"] for m in match_resp.json()}
    assert titles == {"Yakın ilan"}


def test_match_without_radius_keeps_exact_district_behavior(client, monkeypatch):
    """radius_km verilmezse geocode_district hiç çağrılmamalı, eski (bölge
    string tam eşleşmesi) davranış bozulmadan korunmalı."""
    calls = []

    def _tracking_geocode(db, district):
        calls.append(district)
        return _fake_geocode(db, district)

    monkeypatch.setattr(matching, "geocode_district", _tracking_geocode)

    headers = _register(client, "Ofis Geo Test 2", "owner2@geo-test.com")
    client.post(
        "/listings",
        json={"title": "Tam eşleşme", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    client.post(
        "/listings",
        json={"title": "Farklı bölge", "district": "Uskudar", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    lead_resp = client.post(
        "/leads",
        json={"contact_phone": "5551112244", "district": "Kadikoy"},
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    titles = {m["title"] for m in match_resp.json()}
    assert titles == {"Tam eşleşme"}
    assert calls == []


def test_geocode_failure_falls_back_to_exact_district_match(client, monkeypatch):
    """Lead'in bölgesi geocode edilemiyorsa (None dönerse) sert hata yerine
    eski bölge string eşleşmesine sessizce düşülmeli."""
    monkeypatch.setattr(matching, "geocode_district", lambda db, district: None)

    headers = _register(client, "Ofis Geo Test 3", "owner3@geo-test.com")
    client.post(
        "/listings",
        json={"title": "Bilinmeyen bölge ilanı", "district": "Bilinmeyenbolge", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    lead_resp = client.post(
        "/leads",
        json={"contact_phone": "5551112255", "district": "Bilinmeyenbolge", "radius_km": 5},
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    titles = {m["title"] for m in match_resp.json()}
    assert titles == {"Bilinmeyen bölge ilanı"}


def test_haversine_km_known_distance():
    kadikoy = (40.9833, 29.0333)
    ankara = (39.9334, 32.8597)
    distance = geocoding.haversine_km(*kadikoy, *ankara)
    assert 320 < distance < 380  # gerçek mesafe ~350km


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeHttpClient:
    def __init__(self, payload):
        self._payload = payload
        self.call_count = 0

    def get(self, url, params=None):
        self.call_count += 1
        return _FakeResponse(self._payload)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_geocode_district_caches_after_first_lookup(db_session, monkeypatch):
    # geocoded_districts test'ler arası truncate edilmiyor (kalıcı bir önbellek
    # olduğu için bilinçli) — çakışmayı önlemek için her çalıştırmada benzersiz isim.
    district_name = f"TestBenzersizBolge-{uuid.uuid4().hex[:8]}"
    fake_client = _FakeHttpClient([{"lat": "40.99", "lon": "29.03"}])
    monkeypatch.setattr(geocoding, "get_http_client", lambda: fake_client)

    first = geocoding.geocode_district(db_session, district_name)
    assert first == (40.99, 29.03)
    assert fake_client.call_count == 1

    # İkinci çağrı önbellekten dönmeli, tekrar HTTP isteği atmamalı.
    second = geocoding.geocode_district(db_session, district_name.lower())
    assert second == (40.99, 29.03)
    assert fake_client.call_count == 1
