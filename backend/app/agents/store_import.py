"""Apify ile Sahibinden mağaza sayfası aktarımı (POST /listings/import-store).

Danışman mağazasının URL'sini verir (örn. toycuemlak.sahibinden.com); sayfa
Apify üzerinden (Apify'ın kendi proxy havuzuyla) çekilir — backend Sahibinden'e
DOĞRUDAN istek atmaz (sunucudan atılan istekler Cloudflare 403 yiyor, bkz.
listing_import.fetch_page'in kaderi). Dönen ham HTML, "kaynak yapıştır" toplu
aktarımının KULLANDIĞI AYNI parser'dan (parse_sahibinden_portfolio) geçirilir —
Apify sadece fetch adımını üstlenir, ayrıştırma/inceleme akışı birebir aynıdır:
hiçbir ilan otomatik oluşturulmaz, danışman inceleme kartlarında onaylar;
onaylananlar normal POST /listings ile Postgres'e + (index_listing üzerinden)
ChromaDB emsal endeksine yazılır.

Bot koruması Apify'ı da engelleyebilir — her hata yolu, danışmana mevcut
alternatifleri (kaynak yapıştırma, Voice-to-Listing) hatırlatan tek bir
kullanıcı-dostu mesajla StoreImportError'a çevrilir.
"""

import json
import re
from urllib.parse import urlparse

import httpx

from app.agents.listing_import import parse_sahibinden_portfolio
from app.core.config import settings

APIFY_RUN_SYNC_URL = "https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"

# Apify sync run'ları 30-90 sn sürebilir — paylaşılan get_http_client'ın 10 sn
# timeout'u bilinçli olarak KULLANILMAZ, bu modül kendi cömert timeout'unu kurar.
APIFY_TIMEOUT = httpx.Timeout(120.0, connect=10.0)
APIFY_RUN_TIMEOUT_SECS = 110  # actor tarafındaki tavan, HTTP timeout'tan küçük

# Mağaza subdomain'i: harf/rakam/tire, sahibinden.com'un kendi servis
# subdomain'leri hariç. www.sahibinden.com/... arama linkleri mağaza değildir.
_STORE_HOST_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*\.sahibinden\.com$")
_RESERVED_SUBDOMAINS = {"www", "secure", "banaozel", "destek", "blog", "kurumsal", "s0", "s1", "image"}

# cheerio-scraper'ın pageFunction'ı: sayfanın HAM HTML'ini döndürür — ayrıştırma
# Apify'da değil, bizim mevcut parser'ımızda yapılır (tek doğruluk kaynağı).
_PAGE_FUNCTION = """async function pageFunction(context) {
    return { url: context.request.url, html: context.body };
}"""

FALLBACK_SUGGESTION = (
    "Alternatif olarak mağaza sayfanızın kaynağını kopyalayıp 'Toplu Aktarım'a "
    "yapıştırabilir ya da Voice-to-Listing (Sesle İlan Ekleme) özelliğini kullanabilirsiniz."
)


class UnsupportedStoreUrlError(Exception):
    """Verilen URL bir Sahibinden mağaza adresi değil."""


class StoreImportError(Exception):
    """Mağaza aktarımı başarısız (yapılandırma eksik, Apify/bot koruması hatası)."""


def validate_store_url(url: str) -> str:
    """URL'yi doğrular ve normalize eder (https, path'siz mağaza kökü).
    Danışman genelde çıplak "toycuemlak.sahibinden.com" yazar — şema eklenir."""
    raw = (url or "").strip()
    if not raw:
        raise UnsupportedStoreUrlError("Mağaza adresi boş olamaz.")
    if "://" not in raw:
        raw = f"https://{raw}"

    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise UnsupportedStoreUrlError("Mağaza adresi http(s) ile başlamalı.")

    host = (parsed.hostname or "").lower()
    subdomain = host.split(".")[0] if host else ""
    if not _STORE_HOST_PATTERN.match(host) or subdomain in _RESERVED_SUBDOMAINS:
        raise UnsupportedStoreUrlError(
            "Bu adres bir Sahibinden mağaza adresi değil — örnek biçim: magazaadi.sahibinden.com"
        )
    return f"https://{host}"


def fetch_store_html(store_url: str) -> str:
    """Mağaza sayfasının ham HTML'ini Apify sync run ile çeker. Token yoksa
    '__not_configured__' (route 503'e çevirir); diğer tüm hatalar kullanıcıya
    gösterilebilir tek bir StoreImportError'a düşer."""
    if not settings.apify_token:
        raise StoreImportError("__not_configured__")

    run_input = {
        "startUrls": [{"url": store_url}],
        "maxRequestsPerCrawl": 1,
        "proxyConfiguration": {"useApifyProxy": True},
        "pageFunction": _PAGE_FUNCTION,
    }
    endpoint = APIFY_RUN_SYNC_URL.format(actor_id=settings.apify_actor_id)

    try:
        with httpx.Client(timeout=APIFY_TIMEOUT) as client:
            response = client.post(
                endpoint,
                params={"token": settings.apify_token, "timeout": APIFY_RUN_TIMEOUT_SECS},
                json=run_input,
            )
            response.raise_for_status()
            items = response.json()
    except httpx.TimeoutException as exc:
        raise StoreImportError(
            f"Mağaza sayfası zaman aşımına uğradı. {FALLBACK_SUGGESTION}"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise StoreImportError(
            f"Mağaza sayfası alınamadı (Apify durum kodu {exc.response.status_code}). {FALLBACK_SUGGESTION}"
        ) from exc
    except (httpx.RequestError, json.JSONDecodeError, ValueError) as exc:
        raise StoreImportError(f"Mağaza sayfasına ulaşılamadı. {FALLBACK_SUGGESTION}") from exc

    if not isinstance(items, list) or not items:
        raise StoreImportError(f"Mağaza sayfası okunamadı (boş yanıt). {FALLBACK_SUGGESTION}")

    html = items[0].get("html") if isinstance(items[0], dict) else None
    if not html or not isinstance(html, str):
        raise StoreImportError(f"Mağaza sayfası okunamadı. {FALLBACK_SUGGESTION}")
    return html


def import_store_listings(url: str) -> list[dict]:
    """URL doğrulama → Apify fetch → mevcut portföy parser'ı. Boş sonuç da
    hata sayılır (bot koruması ara sayfası HTML dönebilir ama içinde ilan
    kartı olmaz) — danışmana fallback önerisiyle bildirilir."""
    store_url = validate_store_url(url)
    html = fetch_store_html(store_url)

    try:
        listings = parse_sahibinden_portfolio(html)
    except Exception as exc:  # ayrıştırıcı best-effort ama beklenmedik HTML'e karşı emniyet
        raise StoreImportError(f"Mağaza sayfası ayrıştırılamadı. {FALLBACK_SUGGESTION}") from exc

    if not listings:
        raise StoreImportError(
            f"Mağaza sayfasında ilan bulunamadı — bot koruması engellemiş olabilir. {FALLBACK_SUGGESTION}"
        )
    return listings
