import json
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.http import get_http_client

SUPPORTED_DOMAINS = {"sahibinden.com", "www.sahibinden.com"}


class UnsupportedListingSiteError(Exception):
    """Desteklenmeyen bir domain'den ilan linki verildi."""


class ListingFetchError(Exception):
    """Sayfa alınamadı (ağ hatası, zaman aşımı, 4xx/5xx)."""


def fetch_page(url: str) -> str:
    try:
        with get_http_client() as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.TimeoutException as exc:
        raise ListingFetchError("Sayfa zaman aşımına uğradı, tekrar deneyin.") from exc
    except httpx.HTTPStatusError as exc:
        raise ListingFetchError(f"Sayfa alınamadı (durum kodu {exc.response.status_code}).") from exc
    except httpx.RequestError as exc:
        raise ListingFetchError("Sayfaya ulaşılamadı, linki kontrol edin.") from exc


def _parse_turkish_price(text: str) -> float | None:
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.]", "", text)
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_json_ld(soup: BeautifulSoup) -> dict:
    """Çoğu ilan sitesi schema.org JSON-LD gömer — CSS class'larından daha
    kararlı bir kaynak, siteye özel seçicilerden önce bunu dene."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, list):
            data = next((item for item in data if isinstance(item, dict)), {})
        if isinstance(data, dict) and data:
            return data
    return {}


def _meta_content(soup: BeautifulSoup, property_name: str) -> str | None:
    tag = soup.find("meta", attrs={"property": property_name})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


def parse_sahibinden(html: str) -> dict:
    """Sahibinden ilan sayfasından alanları çıkarır. Seçiciler genel bilgiye
    dayalı en iyi tahmin — gerçek linklerle test edilip ince ayar gerekebilir.
    Her alan bağımsız olarak best-effort'tur; biri bulunamazsa None döner,
    tüm işlem başarısız sayılmaz."""
    soup = BeautifulSoup(html, "lxml")
    json_ld = _extract_json_ld(soup)

    title = json_ld.get("name") or _meta_content(soup, "og:title")
    if not title:
        h1 = soup.find("h1", class_=re.compile("classifiedDetailTitle|classifiedTitle", re.I))
        title = h1.get_text(strip=True) if h1 else None

    price_text = None
    offers = json_ld.get("offers")
    if isinstance(offers, dict) and offers.get("price"):
        price_text = str(offers["price"])
    if not price_text:
        price_el = soup.find(class_=re.compile("classifiedInfo.*price|price-wrapper", re.I))
        price_text = price_el.get_text(strip=True) if price_el else None
    price = _parse_turkish_price(price_text) if price_text else None

    district = None
    location_el = soup.find(class_=re.compile("classifiedInfo.*location|location-text", re.I))
    if location_el:
        location_text = location_el.get_text(" ", strip=True)
        parts = [p for p in re.split(r"[/,]", location_text) if p.strip()]
        if parts:
            district = parts[-1].strip()

    room_count = None
    room_label = soup.find(string=re.compile(r"^\s*\d\s*\+\s*\d\s*$"))
    if room_label:
        room_count = room_label.strip()

    square_meters = None
    sqm_label = soup.find(string=re.compile(r"\d+\s*(?:m2|m²)", re.I))
    if sqm_label:
        match = re.search(r"(\d+)\s*(?:m2|m²)", sqm_label, re.I)
        if match:
            square_meters = int(match.group(1))

    return {
        "title": title,
        "district": district,
        "price": price,
        "room_count": room_count,
        "square_meters": square_meters,
    }


def extract_listing(url: str) -> dict:
    domain = urlparse(url).netloc.lower()
    if domain not in SUPPORTED_DOMAINS:
        raise UnsupportedListingSiteError(
            "Bu site şu an desteklenmiyor. Şimdilik sadece Sahibinden linkleri destekleniyor."
        )
    html = fetch_page(url)
    return parse_sahibinden(html)
