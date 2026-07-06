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


def _extract_json_ld_all(soup: BeautifulSoup) -> list[dict]:
    """Sayfadaki tüm schema.org JSON-LD bloklarını döner — bir sayfada hem ilan
    (Product/RealEstateListing) hem BreadcrumbList olabilir."""
    blocks: list[dict] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, list):
            blocks.extend(item for item in data if isinstance(item, dict))
        elif isinstance(data, dict) and data:
            blocks.append(data)
    return blocks


def _extract_json_ld(soup: BeautifulSoup) -> dict:
    """Çoğu ilan sitesi schema.org JSON-LD gömer — CSS class'larından daha
    kararlı bir kaynak, siteye özel seçicilerden önce bunu dene."""
    blocks = _extract_json_ld_all(soup)
    return blocks[0] if blocks else {}


def _meta_content(soup: BeautifulSoup, property_name: str) -> str | None:
    tag = soup.find("meta", attrs={"property": property_name})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


def _fold_turkish_i(text: str) -> str:
    """Python'un str.lower()'ı Türkçe büyük "İ"yi TEK bir küçük harfe değil,
    "i" + görünmez bir COMBINING DOT ABOVE karakterine ayırır (Unicode'un
    varsayılan, yerel-ayardan bağımsız case-folding kuralı) — bu da
    "KİRALIK".lower()'ı "kiralik" değil "ki̇ralik" yapıp aramamızı sessizce
    kırıyordu (gerçek bug, "kiralık" ilanların hepsi None'a düşüyordu).
    Çözüm: İ/I/ı'nın hepsini büyük/küçük harf farkı önemsemeden düz "i"ye
    indirip sonra normal .lower() uyguluyoruz."""
    return text.replace("İ", "i").replace("I", "i").replace("ı", "i").lower()


def _detect_listing_type(*texts: str | None) -> str | None:
    """Başlık/etiket metninde "kiralık" ya da "satılık" ifadesi arar — Sahibinden
    ilan başlıklarında ve kart etiketlerinde bu neredeyse her zaman geçer.
    İkisi de geçiyorsa veya hiçbiri geçmiyorsa None döner (danışman elle seçer)."""
    combined = _fold_turkish_i(" ".join(t for t in texts if t))
    has_rent = "kiralik" in combined
    has_sale = "satilik" in combined
    if has_rent and not has_sale:
        return "rent"
    if has_sale and not has_rent:
        return "sale"
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

    room_count, square_meters = _shared_room_and_sqm(soup)
    listing_type = _detect_listing_type(title)
    cover_photo_url = _meta_content(soup, "og:image")

    return {
        "title": title,
        "district": district,
        "price": price,
        "room_count": room_count,
        "square_meters": square_meters,
        "listing_type": listing_type,
        "cover_photo_url": cover_photo_url,
    }


def _shared_room_and_sqm(soup: BeautifulSoup) -> tuple[str | None, int | None]:
    """Oda sayısı (2+1 kalıbı) ve m² her iki portalda da serbest metinde geçer —
    siteye özel seçici gerektirmeyen ortak best-effort çıkarım."""
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
    return room_count, square_meters


def parse_emlakjet(html: str) -> dict:
    """Emlakjet ilan sayfasından alanları çıkarır. Sahibinden'deki gibi JSON-LD
    öncelikli, best-effort — gerçek yapıştırılmış kaynaklarla doğrulanması
    gerekiyor. Her alan bağımsızdır; bulunamayan alan None döner."""
    soup = BeautifulSoup(html, "lxml")
    json_ld_blocks = _extract_json_ld_all(soup)
    listing_ld = next(
        (
            b
            for b in json_ld_blocks
            if b.get("@type") in ("Product", "RealEstateListing", "Offer", "Residence")
        ),
        json_ld_blocks[0] if json_ld_blocks else {},
    )

    title = listing_ld.get("name") or _meta_content(soup, "og:title")
    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else None

    price_text = None
    offers = listing_ld.get("offers")
    if isinstance(offers, dict) and offers.get("price"):
        price_text = str(offers["price"])
    if not price_text:
        price_el = soup.find(class_=re.compile("price", re.I))
        price_text = price_el.get_text(strip=True) if price_el else None
    price = _parse_turkish_price(price_text) if price_text else None

    breadcrumb = next((b for b in json_ld_blocks if b.get("@type") == "BreadcrumbList"), None)
    breadcrumb_items = []
    if breadcrumb:
        breadcrumb_items = [
            i.get("name") or (i.get("item") or {}).get("name")
            for i in breadcrumb.get("itemListElement", [])
            if isinstance(i, dict)
        ]
        breadcrumb_items = [i for i in breadcrumb_items if i]

    # İlçe: JSON-LD adresinden (addressLocality ilçeye denk gelir); yoksa
    # breadcrumb'ın sondan bir önceki halkası genelde ilçe sayfasıdır.
    district = None
    address = listing_ld.get("address")
    if isinstance(address, dict):
        district = address.get("addressLocality") or address.get("addressRegion")
    if not district and len(breadcrumb_items) >= 2:
        district = breadcrumb_items[-2]

    room_count, square_meters = _shared_room_and_sqm(soup)
    # Breadcrumb'ın son halkası genelde ilanın kendi adı ("Satılık Daire
    # 12345") — başlıkta geçmese de burada "satılık"/"kiralık" geçebilir.
    listing_type = _detect_listing_type(title, breadcrumb_items[-1] if breadcrumb_items else None)
    cover_photo_url = _meta_content(soup, "og:image")

    return {
        "title": title,
        "district": district,
        "price": price,
        "room_count": room_count,
        "square_meters": square_meters,
        "listing_type": listing_type,
        "cover_photo_url": cover_photo_url,
    }


def parse_sahibinden_portfolio(html: str) -> list[dict]:
    """Danışmanın Sahibinden'deki KENDİ portföyünün listelendiği sayfadan
    ("İlanlarım" / mağaza sayfası) tüm ilanları TEK seferde ayrıştırır.
    Bu, tek ilan sayfasından farklı bir HTML yapısı kullanır (`.classified`
    kartları) — bu yüzden ayrı bir fonksiyon. Danışman bu sayfanın kaynağını
    da (Ctrl+U → view-source) kendi tarayıcısından kopyalayıp yapıştırır;
    outbound istek yok, sadece yapıştırılan metin ayrıştırılır.

    Sahibinden aynı ilanı bazen (öne çıkan/vitrin) kartıyla sayfada iki kez
    gösteriyor — kartın data-box-url'i (ilanın kalıcı detay linki) ile
    içerik-bazlı tekilleştirme yapılır. Her kart bağımsız best-effort'tur;
    bir kart eksik alan içerse bile diğerleri etkilenmez."""
    soup = BeautifulSoup(html, "lxml")
    cards = soup.find_all("div", class_="classified")

    results: list[dict] = []
    seen_urls: set[str] = set()
    for card in cards:
        source_url = card.get("data-box-url")
        if source_url:
            if source_url in seen_urls:
                continue
            seen_urls.add(source_url)

        title_el = card.select_one("p.title a")
        title = title_el.get_text(strip=True) if title_el else None

        price_el = card.select_one("p.price")
        price = _parse_turkish_price(price_el.get_text(strip=True)) if price_el else None

        district = None
        location_el = card.select_one("p.location")
        if location_el:
            parts = [p for p in re.split(r"[/,]", location_el.get_text(" ", strip=True)) if p.strip()]
            if parts:
                district = parts[-1].strip()

        room_el = card.select_one("p.rooms")
        room_count = room_el.get_text(strip=True) if room_el else None

        square_meters = None
        sqm_el = card.select_one("p.m2")
        if sqm_el:
            match = re.search(r"(\d+)", sqm_el.get_text(strip=True))
            if match:
                square_meters = int(match.group(1))

        # Badge ("SATILIK"/"KİRALIK") kartta ayrı bir alan olarak geçiyor ve
        # başlıktan daha güvenilir bir sinyal — o yoksa başlığa düşülür.
        badge_el = card.select_one(".breadcrumb-badge")
        listing_type = _detect_listing_type(
            badge_el.get_text(strip=True) if badge_el else None, title
        )

        img_el = card.select_one(".classified-image img")
        cover_photo_url = img_el.get("src") if img_el else None

        if not title and price is None and not district:
            continue  # boş/tanınmayan kart, atla

        results.append(
            {
                "title": title,
                "district": district,
                "price": price,
                "room_count": room_count,
                "square_meters": square_meters,
                "listing_type": listing_type,
                "cover_photo_url": cover_photo_url,
            }
        )
    return results


def detect_source(html: str) -> str:
    """Yapıştırılan sayfa kaynağının hangi portala ait olduğunu tahmin eder.
    canonical/og:url en güvenilir sinyal; bulunamazsa ham metinde domain aranır.
    Varsayılan sahibinden (ilk desteklenen portal)."""
    soup = BeautifulSoup(html, "lxml")
    canonical = soup.find("link", rel="canonical")
    candidates = [
        (canonical.get("href") or "") if canonical else "",
        _meta_content(soup, "og:url") or "",
    ]
    for candidate in candidates:
        domain = urlparse(candidate).netloc.lower()
        if "emlakjet" in domain:
            return "emlakjet"
        if "sahibinden" in domain:
            return "sahibinden"
    if "emlakjet.com" in html[:20000]:
        return "emlakjet"
    return "sahibinden"


def parse_listing_html(html: str) -> dict:
    """Danışmanın yapıştırdığı sayfa kaynağını portala göre ayrıştırır —
    POST /listings/extract-from-html'in kullandığı tek giriş noktası."""
    if detect_source(html) == "emlakjet":
        return parse_emlakjet(html)
    return parse_sahibinden(html)


def extract_listing(url: str) -> dict:
    domain = urlparse(url).netloc.lower()
    if domain not in SUPPORTED_DOMAINS:
        raise UnsupportedListingSiteError(
            "Bu site şu an desteklenmiyor. Şimdilik sadece Sahibinden linkleri destekleniyor."
        )
    html = fetch_page(url)
    return parse_sahibinden(html)
