from app.agents import listing_import

FAKE_SAHIBINDEN_HTML = """
<html>
<head>
<script type="application/ld+json">
{"@type": "Product", "name": "Deniz manzaralı 3+1 daire", "offers": {"price": "2500000"}}
</script>
</head>
<body>
  <div class="classifiedInfo-location">Istanbul / Kadikoy / Fenerbahce</div>
  <strong>3+1</strong>
  <span>Brüt 140 m2</span>
</body>
</html>
"""


def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "supersecret123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_parse_sahibinden_extracts_fields_from_json_ld_and_html():
    fields = listing_import.parse_sahibinden(FAKE_SAHIBINDEN_HTML)
    assert fields["title"] == "Deniz manzaralı 3+1 daire"
    assert fields["price"] == 2500000.0
    assert fields["district"] == "Fenerbahce"
    assert fields["room_count"] == "3+1"
    assert fields["square_meters"] == 140


def test_parse_turkish_price_handles_thousands_separator():
    assert listing_import._parse_turkish_price("2.500.000 TL") == 2500000.0
    assert listing_import._parse_turkish_price("") is None


def test_extract_from_url_requires_auth(client):
    resp = client.post("/listings/extract-from-url", json={"url": "https://www.sahibinden.com/ilan/123"})
    assert resp.status_code == 401


def test_extract_from_url_rejects_unsupported_domain(client):
    headers = _register(client, "Ofis Extract Test 1", "owner1@extract-test.com")
    resp = client.post(
        "/listings/extract-from-url",
        json={"url": "https://example.com/ilan/1"},
        headers=headers,
    )
    assert resp.status_code == 400


def test_extract_from_url_returns_parsed_fields(client, monkeypatch):
    headers = _register(client, "Ofis Extract Test 2", "owner2@extract-test.com")
    monkeypatch.setattr(listing_import, "fetch_page", lambda url: FAKE_SAHIBINDEN_HTML)

    resp = client.post(
        "/listings/extract-from-url",
        json={"url": "https://www.sahibinden.com/ilan/456"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Deniz manzaralı 3+1 daire"
    assert body["price"] == 2500000.0
    assert body["room_count"] == "3+1"


def test_extract_from_url_returns_502_on_fetch_failure(client, monkeypatch):
    headers = _register(client, "Ofis Extract Test 3", "owner3@extract-test.com")

    def _raise(url):
        raise listing_import.ListingFetchError("Sayfaya ulaşılamadı, linki kontrol edin.")

    monkeypatch.setattr(listing_import, "fetch_page", _raise)

    resp = client.post(
        "/listings/extract-from-url",
        json={"url": "https://www.sahibinden.com/ilan/789"},
        headers=headers,
    )
    assert resp.status_code == 502


def test_extract_from_html_requires_auth(client):
    resp = client.post("/listings/extract-from-html", json={"html": FAKE_SAHIBINDEN_HTML})
    assert resp.status_code == 401


def test_extract_from_html_returns_parsed_fields_without_fetching(client):
    """Sahibinden'in bot koruması yüzünden fetch adımı hiç yok — sadece
    yapıştırılan HTML parse ediliyor, hiçbir outbound istek atılmıyor."""
    headers = _register(client, "Ofis Extract Test 4", "owner4@extract-test.com")
    resp = client.post(
        "/listings/extract-from-html",
        json={"html": FAKE_SAHIBINDEN_HTML},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Deniz manzaralı 3+1 daire"
    assert body["district"] == "Fenerbahce"
    assert body["room_count"] == "3+1"
    assert body["square_meters"] == 140


def test_extract_from_html_handles_garbage_gracefully(client):
    headers = _register(client, "Ofis Extract Test 5", "owner5@extract-test.com")
    resp = client.post(
        "/listings/extract-from-html",
        json={"html": "<html><body>alakasız bir sayfa</body></html>"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] is None
    assert body["price"] is None
