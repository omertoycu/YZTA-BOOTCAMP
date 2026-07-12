"""Apify mağaza aktarımı (app/agents/store_import.py + POST /listings/import-store).

Apify'a gerçek istek atılmaz — fetch adımı monkeypatch'lenir, ayrıştırma
mevcut parse_sahibinden_portfolio'dan (test_listing_extract'taki fixture ile)
geçer. Amaç: URL doğrulama, yapılandırma eksikliği (503), bot koruması/boş
sonuç fallback mesajı (502) ve mutlu yol."""

import pytest

from app.agents import store_import
from app.agents.store_import import UnsupportedStoreUrlError, validate_store_url
from app.core.config import settings
from tests.test_listing_extract import FAKE_SAHIBINDEN_PORTFOLIO_HTML


def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "Supersecret123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# --- validate_store_url (saf birim testleri) ---


def test_validate_store_url_accepts_and_normalizes():
    assert validate_store_url("toycuemlak.sahibinden.com") == "https://toycuemlak.sahibinden.com"
    assert validate_store_url("https://toycuemlak.sahibinden.com/ilanlar?x=1") == "https://toycuemlak.sahibinden.com"
    assert validate_store_url("  HTTP://Magaza-1.sahibinden.com  ") == "https://magaza-1.sahibinden.com"


@pytest.mark.parametrize(
    "url",
    [
        "",
        "sahibinden.com",
        "www.sahibinden.com",
        "secure.sahibinden.com",
        "evil.com",
        "toycuemlak.sahibinden.com.evil.com",
        "ftp://magaza.sahibinden.com",
        "emlakjet.com/magaza",
    ],
)
def test_validate_store_url_rejects_non_store_addresses(url):
    with pytest.raises(UnsupportedStoreUrlError):
        validate_store_url(url)


# --- Route ---


def test_import_store_returns_503_when_apify_not_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "apify_token", None)
    headers = _register(client, "Ofis Store 1", "owner@store-1.com")

    resp = client.post(
        "/listings/import-store", json={"url": "toycuemlak.sahibinden.com"}, headers=headers
    )
    assert resp.status_code == 503


def test_import_store_returns_400_for_invalid_url(client, monkeypatch):
    monkeypatch.setattr(settings, "apify_token", "test-token")
    headers = _register(client, "Ofis Store 2", "owner@store-2.com")

    resp = client.post("/listings/import-store", json={"url": "www.sahibinden.com"}, headers=headers)
    assert resp.status_code == 400
    assert "mağaza" in resp.json()["detail"].lower()


def test_import_store_happy_path_reuses_portfolio_parser(client, monkeypatch):
    monkeypatch.setattr(settings, "apify_token", "test-token")
    monkeypatch.setattr(store_import, "fetch_store_html", lambda url: FAKE_SAHIBINDEN_PORTFOLIO_HTML)
    headers = _register(client, "Ofis Store 3", "owner@store-3.com")

    resp = client.post(
        "/listings/import-store", json={"url": "toycuemlak.sahibinden.com"}, headers=headers
    )
    assert resp.status_code == 200
    listings = resp.json()["listings"]
    # Fixture'da 4 kart var ama biri (vitrin kopyası) aynı data-box-url'e sahip —
    # tekilleştirme sonrası 3 taslak (bkz. parse_sahibinden_portfolio).
    assert len(listings) == 3
    assert listings[0]["title"] == "Altıparmak'ta Satılık 3+1 Daire"
    assert listings[0]["price"] == 2_500_000
    assert listings[0]["district"] == "Osmangazi"


def test_import_store_returns_502_with_voice_fallback_when_page_unreadable(client, monkeypatch):
    """Bot koruması ara sayfası HTML döndürebilir ama içinde ilan kartı olmaz —
    danışmana alternatif yollar (Voice-to-Listing) önerilmeli."""
    monkeypatch.setattr(settings, "apify_token", "test-token")
    monkeypatch.setattr(store_import, "fetch_store_html", lambda url: "<html><body>blocked</body></html>")
    headers = _register(client, "Ofis Store 4", "owner@store-4.com")

    resp = client.post(
        "/listings/import-store", json={"url": "toycuemlak.sahibinden.com"}, headers=headers
    )
    assert resp.status_code == 502
    assert "Voice-to-Listing" in resp.json()["detail"]


def test_import_store_returns_502_when_apify_call_fails(client, monkeypatch):
    monkeypatch.setattr(settings, "apify_token", "test-token")

    def _fail(url):
        raise store_import.StoreImportError(
            f"Mağaza sayfasına ulaşılamadı. {store_import.FALLBACK_SUGGESTION}"
        )

    monkeypatch.setattr(store_import, "fetch_store_html", _fail)
    headers = _register(client, "Ofis Store 5", "owner@store-5.com")

    resp = client.post(
        "/listings/import-store", json={"url": "toycuemlak.sahibinden.com"}, headers=headers
    )
    assert resp.status_code == 502
    assert "Voice-to-Listing" in resp.json()["detail"]
