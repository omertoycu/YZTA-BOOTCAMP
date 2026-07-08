import re

from google import genai
from google.genai import types

from app.core.config import settings
from app.models.listing import Listing

MODEL_NAME = "gemini-2.5-flash"

# BİLİNÇLİ SDK AYRIMI: diğer tüm agent'lar (whatsapp_extract.py, reply_draft.py,
# voice_listing.py, match_ranking.py...) `google-generativeai` (artık Google
# tarafından durdurulmuş "deprecated-generative-ai-python") kullanıyor. O
# kütüphane Gemini 2.0+ modellerinin web arama (`google_search`) aracını
# güvenilir desteklemiyor (bkz. google-gemini/deprecated-generative-ai-python
# issue #667, çözümsüz kaldı). Bu yüzden SADECE bu dosya, Google'ın güncel
# `google-genai` SDK'sını (`from google import genai`, YUKARIDAKİ import —
# `import google.generativeai as genai` DEĞİL) kullanıyor. Aynı GEMINI_API_KEY
# her iki kütüphane için de geçerli.
_PROPERTY_TYPE_LABELS = {
    "residential": "konut (daire/villa)",
    "commercial": "iş yeri/ticari",
    "land": "arsa",
}
_LISTING_TYPE_LABELS = {"sale": "satılık", "rent": "kiralık"}

# Gemini API'de google_search aracı ile response_mime_type="application/json"
# AYNI ANDA kullanılamıyor ("Function calling with a response mime type:
# application/json is unsupported" hatası) — bu yüzden yanıt JSON değil, basit
# satır bazlı bir formatta istenip aşağıdaki regex'lerle ayrıştırılıyor.
PROMPT_TEMPLATE = """Sen bir emlak piyasası analistisin. Google araması kullanarak, aşağıdaki \
özelliklere sahip bir gayrimenkulle KARŞILAŞTIRILABİLİR, güncel {listing_type_label} ilanların \
Türkiye'deki tipik fiyat aralığını araştır:

Konum: {district}, Türkiye
Emlak tipi: {property_type_label}
{room_count_line}{square_meters_line}
Bulduğun emsallere dayanarak yanıtını TAM OLARAK aşağıdaki formatta ver, başka HİÇBİR metin, \
markdown ya da JSON ekleme:

ALT_SINIR: <TL cinsinden tahmini alt sınır, güvenilir bir veri bulamadıysan BILINMIYOR>
UST_SINIR: <TL cinsinden tahmini üst sınır, güvenilir bir veri bulamadıysan BILINMIYOR>
OZET: <bulgularının 1-2 cümlelik Türkçe özeti>"""

_LINE_PATTERN = re.compile(r"^\s*(ALT_SINIR|UST_SINIR|OZET)\s*:\s*(.+?)\s*$", re.MULTILINE)
_NUMBER_PATTERN = re.compile(r"[\d.,]+")


class MarketPriceCheckError(Exception):
    """Web'den piyasa doğrulaması yapılamadı (yapılandırma eksik, LLM/arama hatası)."""


def _get_client() -> "genai.Client":
    if not settings.gemini_api_key:
        raise MarketPriceCheckError("__not_configured__")
    return genai.Client(api_key=settings.gemini_api_key)


def _parse_amount(raw: str) -> float | None:
    if "bilinmiyor" in raw.strip().lower():
        return None
    match = _NUMBER_PATTERN.search(raw)
    if not match:
        return None
    # Türkçe biçimde binlik ayraç "." ondalık ayraç ","; sadece rakamları alıp
    # kalan noktalama işaretlerini (binlik ayraç) temizlemek yeterli — TL
    # tutarlarında kuruş hassasiyeti gerekmiyor.
    digits = re.sub(r"[.,]", "", match.group(0))
    try:
        return float(digits)
    except ValueError:
        return None


def _extract_sources(response) -> list[dict]:
    """Şeffaflık için: AI'ın hangi web kaynaklarını kullandığını gösterir —
    tamamı best-effort (attribute'lar SDK sürümüne/yanıta göre eksik olabilir),
    herhangi bir eksiklik sessizce boş kaynak listesine düşer."""
    sources: list[dict] = []
    try:
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            metadata = getattr(candidate, "grounding_metadata", None)
            chunks = getattr(metadata, "grounding_chunks", None) or []
            for chunk in chunks:
                web = getattr(chunk, "web", None)
                url = getattr(web, "uri", None)
                title = getattr(web, "title", None)
                if url:
                    sources.append({"title": title or url, "url": url})
    except Exception:
        return []
    return sources


def fetch_market_price_check(listing: Listing) -> dict:
    """Ofisin kendi portföyüyle sınırlı ChromaDB k-NN önerisinin (bkz.
    app/agents/pricing.py: suggest_price_range) aksine, Gemini'nin Google
    arama (grounding) aracıyla WEB GENELİNDE muadil ilanları araştırıp bir
    aralık + kısa özet üretir. Backend hiçbir siteye doğrudan istek atmıyor
    (scraping YOK) — arama tamamen Gemini'nin kendi altyapısında yapılıyor.

    Kesin bir fiyat iddiası DEĞİL, AI'ın web'de bulduğu emsallere dayalı bir
    tahmin (bkz. suggest_price_range'deki aynı ilke) — bu yüzden `sources`
    alanıyla şeffaf: danışman hangi kaynaklara dayanıldığını görebilir.

    TAMAMEN best-effort: yapılandırma eksikse ya da arama/ayrıştırma
    HERHANGİ bir şekilde başarısız olursa (ağ hatası, Gemini kredisi bitmiş
    olması — bkz. CLAUDE.md, beklenmeyen yanıt biçimi) sert hata fırlatmaz,
    `has_market_data=False` ile döner — çağıran route'u asla kırmaz (aynı
    desen: app/agents/match_ranking.py)."""
    try:
        client = _get_client()
        room_count_line = f"Oda sayısı: {listing.room_count}\n" if listing.property_type == "residential" else ""
        square_meters_line = f"Metrekare: {listing.square_meters}m2\n" if listing.square_meters else ""
        prompt = PROMPT_TEMPLATE.format(
            listing_type_label=_LISTING_TYPE_LABELS.get(listing.listing_type, listing.listing_type),
            district=listing.district,
            property_type_label=_PROPERTY_TYPE_LABELS.get(listing.property_type, listing.property_type),
            room_count_line=room_count_line,
            square_meters_line=square_meters_line,
        )
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]),
        )
        text = getattr(response, "text", None)
        if not text:
            raise MarketPriceCheckError("Modelden yanıt alınamadı")

        fields = {key: value for key, value in _LINE_PATTERN.findall(text)}
        estimated_min = _parse_amount(fields.get("ALT_SINIR", "BILINMIYOR"))
        estimated_max = _parse_amount(fields.get("UST_SINIR", "BILINMIYOR"))
        summary = fields.get("OZET")
        sources = _extract_sources(response)
    except Exception:  # best-effort: her hata türünde "veri yok" olarak sessizce döner
        return {
            "has_market_data": False,
            "estimated_min": None,
            "estimated_max": None,
            "summary": "Web'den piyasa verisi alınamadı, tekrar deneyin.",
            "sources": [],
        }

    if estimated_min is None and estimated_max is None:
        return {
            "has_market_data": False,
            "estimated_min": None,
            "estimated_max": None,
            "summary": summary or "Bu bölge/tip için web'de güvenilir bir emsal bulunamadı.",
            "sources": sources,
        }

    return {
        "has_market_data": True,
        "estimated_min": estimated_min,
        "estimated_max": estimated_max,
        "summary": summary,
        "sources": sources,
    }
