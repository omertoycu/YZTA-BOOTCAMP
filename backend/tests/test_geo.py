"""Statik il/ilçe/mahalle sözlüğü (app/core/geo.py) ve /geo/* route'ları.

Sözlük repo içine gömülü olduğu için testler deterministik — dış servis yok.
"""
from app.core.geo import infer_city, resolve_location, search_cities, search_districts, search_neighborhoods


def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "Supersecret123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_search_cities_prefix_matches_turkish_insensitively():
    # "b" → B ile başlayan tüm iller, alfabetik
    cities = search_cities("b")
    assert cities[0] == "Balıkesir"
    assert {"Bursa", "Bolu", "Bayburt"} <= set(cities)
    # Aksansız yazım da eşleşmeli
    assert search_cities("istan") == ["İstanbul"]
    assert search_cities("dıyarbak") == ["Diyarbakır"]


def test_search_districts_scoped_to_city():
    assert search_districts("kad", city="İstanbul") == ["Kadıköy"]
    assert search_districts("kad", city="istanbul") == ["Kadıköy"]  # aksansız il adı
    # Şehir verilmeden de çalışır (tüm iller taranır)
    assert "Kadıköy" in search_districts("kadik")


def test_search_neighborhoods_requires_district():
    assert search_neighborhoods("fener") == []
    result = search_neighborhoods("fener", city="İstanbul", district="Kadıköy")
    assert "Fenerbahçe" in result


def test_infer_city_resolves_unique_and_ambiguous_districts():
    assert infer_city("Nilüfer") == "Bursa"
    assert infer_city("Kadıköy") == "İstanbul"
    # "Merkez" 51 ilde var — mahallesiz belirsiz, None dönmeli (yanlış il
    # etiketlemektense boş bırakılır)
    assert infer_city("Merkez") is None
    assert infer_city("Olmayan İlçe") is None


def test_resolve_location_fills_city_from_district():
    resolved = resolve_location(["Kadıköy", "Caferağa Mah."])
    assert resolved == {"city": "İstanbul", "district": "Kadıköy", "neighborhood": "Caferağa"}


def test_geo_routes_require_auth(client):
    assert client.get("/geo/cities?q=b").status_code == 401
    assert client.get("/geo/districts?q=k").status_code == 401
    assert client.get("/geo/neighborhoods?q=f").status_code == 401


def test_geo_routes_return_prefix_matches(client):
    headers = _register(client, "Ofis Geo Test", "owner@geo-test.com")
    resp = client.get("/geo/cities", params={"q": "bu"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json() == ["Burdur", "Bursa"]

    resp = client.get("/geo/districts", params={"q": "nil", "city": "Bursa"}, headers=headers)
    assert resp.json() == ["Nilüfer"]

    resp = client.get(
        "/geo/neighborhoods",
        params={"q": "cafer", "city": "İstanbul", "district": "Kadıköy"},
        headers=headers,
    )
    assert resp.json() == ["Caferağa"]


def test_create_listing_infers_city_from_district(client):
    """Şehir gönderilmeden (portal aktarımı/sesli not akışı) oluşturulan ilanda
    ilçe sözlükte tekil eşleşiyorsa şehir etiketi otomatik konmalı."""
    headers = _register(client, "Ofis Geo Infer Test", "owner@geo-infer-test.com")
    resp = client.post(
        "/listings",
        json={
            "title": "Nilüfer'de 3+1",
            "district": "Nilüfer",
            "neighborhood": "İhsaniye",
            "price": 4500000,
            "room_count": "3+1",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["city"] == "Bursa"
    assert body["district"] == "Nilüfer"
    assert body["neighborhood"] == "İhsaniye"


def test_create_listing_keeps_explicit_city(client):
    headers = _register(client, "Ofis Geo Infer Test 2", "owner2@geo-infer-test.com")
    resp = client.post(
        "/listings",
        json={
            "title": "Kadıköy'de 2+1",
            "city": "İstanbul",
            "district": "Kadıköy",
            "neighborhood": "Caferağa",
            "price": 6500000,
            "room_count": "2+1",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["city"] == "İstanbul"
