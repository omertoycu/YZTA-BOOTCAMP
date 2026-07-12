import json
import re
from datetime import datetime, timedelta, timezone

import google.generativeai as genai

from app.core.ai_limits import MAX_TOKENS_EXTRACTION
from app.core.config import settings

MODEL_NAME = "gemini-2.5-flash"

# --- Ayarlanabilir sabitler (ürün sahibi tarafından belirtilmedi, önerilen
# varsayılanlar — kullanım sonrası kolayca ayarlanabilir) ---
MIN_MESSAGE_LENGTH = 8  # noktalama/emoji temizlendikten sonra minimum karakter
MAX_EXTRACTIONS_PER_24H = 5  # lead başına 24 saatlik kayan pencerede izin verilen Gemini çağrısı
EXTRACTION_WINDOW = timedelta(hours=24)

# Tek başına anlam taşımayan selamlama/onay ifadeleri — TAM eşleşme (substring
# değil), yoksa "merhaba, Kadıköy'de 3+1 arıyorum" gibi gerçek içerikli
# mesajlar yanlışlıkla atlanır.
GREETING_DENYLIST = {
    "merhaba", "selam", "selamlar", "naber", "nasılsın", "iyiyim",
    "tamam", "tamamdır", "ok", "okay", "peki", "olur",
    "teşekkürler", "teşekkür ederim", "sağol", "sağ ol", "eyvallah",
    "günaydın", "iyi günler", "iyi akşamlar", "iyi geceler",
    "evet", "hayır", "anladım",
}

EXTRACTABLE_LEAD_FIELDS = (
    "district",
    "budget_min",
    "budget_max",
    "room_count",
    "radius_km",
    "listing_type_preference",
    "property_type_preference",
)

PROMPT_TEMPLATE = """Bu metin, bir emlak danışmanına WhatsApp üzerinden gelen bir aday mesajıdır \
(örn. "Kadıköy'de 3+1 arıyorum, bütçem 5 milyon TL civarı"). Mesajı oku ve SADECE aşağıdaki JSON \
şemasına uygun, başka hiçbir metin içermeyen bir yanıt üret:

{{
  "district": "<bahsedilen mahalle/ilçe, yoksa null>",
  "budget_min": <TL cinsinden sayı; aralık belirtilmişse alt sınır, yoksa null>,
  "budget_max": <TL cinsinden sayı; bütçe üst sınırı/tek rakam, yoksa null>,
  "room_count": "<örn. '2+1', '3+1'; yoksa null>",
  "radius_km": <"X km çevresi" gibi bir yarıçap belirtilmişse sayı, yoksa null>,
  "listing_type_preference": "<'satılık'/'almak' gibi ifadeler için 'sale'; 'kiralık'/'kira' gibi \
ifadeler için 'rent'; belirtilmemişse null>",
  "property_type_preference": "<'daire'/'konut'/'villa'/'ev' gibi ifadeler için 'residential'; \
'iş yeri'/'ofis'/'dükkan'/'mağaza'/'depo' gibi ifadeler için 'commercial'; 'arsa'/'arazi' için \
'land'; belirtilmemişse null>"
}}

Emin olmadığın alanları null bırak, tahmin yapma. "district" alanına SADECE mahalle/ilçe/il gibi \
idari bir birim yaz — "cadde"/"sokak"/"bulvar" gibi bir sokak adı geçiyorsa onu YOKSAY, mesajda \
ayrıca idari birim varsa onu kullan (yoksa null bırak, sokak adını district'e yazma). Yanıtın \
geçerli JSON olmalı, markdown kod bloğu (```) kullanma.

Mesaj: \"\"\"{message}\"\"\""""


class WhatsAppExtractError(Exception):
    """Alan çıkarımı yapılamadı (yapılandırma eksik, LLM hatası, geçersiz yanıt)."""


def _get_model() -> "genai.GenerativeModel":
    if not settings.gemini_api_key:
        raise WhatsAppExtractError("__not_configured__")
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(MODEL_NAME)


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise WhatsAppExtractError("Model yanıtı ayrıştırılamadı, tekrar deneyin.") from exc


_TURKISH_LOWER_MAP = str.maketrans("İIĞÜŞÖÇ", "iığüşöç")


def _normalize(text: str) -> str:
    """Noktalama/emoji'yi atar (emoji \\w'ye dahil olmadığı için bu regex
    onları da temizler → emoji-only mesajlar doğal olarak trivial sayılır).
    Türkçe büyük/küçük harf dönüşümünü (İ/I çiftleri) elle ele alır çünkü
    Python'ın .lower()'ı 'I' -> 'i' çevirir, 'ı' değil."""
    stripped = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    return " ".join(stripped.translate(_TURKISH_LOWER_MAP).lower().split())


def is_message_trivial(text: str | None) -> bool:
    if not text:
        return True
    normalized = _normalize(text)
    if len(normalized) < MIN_MESSAGE_LENGTH:
        return True
    return normalized in GREETING_DENYLIST


def _extractions_in_current_window(
    extraction_count: int, last_extraction_at: datetime | None, now: datetime
) -> int:
    if last_extraction_at is None or now - last_extraction_at > EXTRACTION_WINDOW:
        return 0
    return extraction_count


def should_run_extraction(
    *,
    message_type: str,
    message_body: str | None,
    district: str | None,
    budget_max,
    room_count: str | None,
    extraction_count: int,
    last_extraction_at: datetime | None,
    now: datetime | None = None,
    force: bool = False,
) -> bool:
    """Gemini'yi ÇAĞIRMADAN ÖNCE maliyet kapısı. force=True (danışmanın manuel
    "Yeniden Analiz Et" tetiklemesi) SADECE 'zaten tüm alanlar dolu'
    atlamasını bypass eder — 24 saatlik hız sınırı force ile de ATLANMAZ."""
    now = now or datetime.now(timezone.utc)

    if not force:
        if message_type != "text" or not message_body:
            return False
        if is_message_trivial(message_body):
            return False
        if district and budget_max is not None and room_count:
            return False
    elif not message_body or not message_body.strip():
        return False

    return _extractions_in_current_window(extraction_count, last_extraction_at, now) < MAX_EXTRACTIONS_PER_24H


def compute_new_extraction_counters(
    extraction_count: int, last_extraction_at: datetime | None, now: datetime | None = None
) -> tuple[int, datetime]:
    """Gemini'ye FİİLEN bir çağrı yapıldıktan sonra çağrılmalı (başarılı/
    başarısız fark etmez — maliyet zaten oluştu). __not_configured__ hiç çağrı
    yapmadığı için bu fonksiyon o durumda ÇAĞRILMAMALI."""
    now = now or datetime.now(timezone.utc)
    current = _extractions_in_current_window(extraction_count, last_extraction_at, now)
    return current + 1, now


def extract_lead_fields(message_text: str) -> dict:
    """WhatsApp mesaj metnini (tek mesaj ya da birleştirilmiş konuşma geçmişi)
    Gemini'ye gönderip district/budget_min/budget_max/room_count/radius_km
    çıkarır. Hiçbir şey otomatik yazılmaz — çağıran taraf (intake.py: fill-only
    otomatik uygulama; leads.py: taslak olarak danışman onayına sunma) yazma
    kararını kendi verir."""
    model = _get_model()
    prompt = PROMPT_TEMPLATE.format(message=message_text)
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "max_output_tokens": MAX_TOKENS_EXTRACTION,
            },
        )
    except Exception as exc:  # Gemini SDK'sı tek bir ortak hata tipi sağlamıyor
        raise WhatsAppExtractError(f"Mesaj işlenemedi: {exc}") from exc

    text = getattr(response, "text", None)
    if not text:
        raise WhatsAppExtractError("Modelden yanıt alınamadı, tekrar deneyin.")

    data = _parse_json_response(text)
    return {field: data.get(field) for field in EXTRACTABLE_LEAD_FIELDS}
