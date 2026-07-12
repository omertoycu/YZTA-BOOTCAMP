"""Hibrit aday/konuşma özeti — yanıt taslağı prompt'una sohbet geçmişi yerine
TEK CÜMLE enjekte etmek için (token tasarrufu, "Summarizer Node").

İki katman:

1. **Deterministik (varsayılan, sıfır Gemini maliyeti):** Adayın zaten yapısal
   tutulan alanlarından (bölge/bütçe/oda/tip) kod ile cümle kurulur — örn.
   "Müşteri Nilüfer'de 20.000 TL'ye kadar 3+1 kiralık konut arıyor". Extraction
   zaten bu alanları dolduruyor; konuşmanın sıkıştırılmış hali budur.
2. **LLM fallback (nadir, önbellekli):** Yapısal alanların HİÇBİRİ dolu değil
   ama konuşma uzamışsa (extraction'ın tek tek mesajlardan çıkaramadığı dağınık
   bir bağlam olabilir) son mesajlar Gemini'yle bir kez özetlenip
   leads.conversation_summary'ye yazılır (migration 0026) — her taslakta
   yeniden üretilmez, extraction'ın 5/24s bütçesinden düşer.

Otomatik WhatsApp akışı (whatsapp_bot) SADECE deterministik katmanı kullanır —
webhook başına ek Gemini çağrısı asla eklenmez.
"""

from datetime import datetime, timedelta, timezone

import google.generativeai as genai

from app.agents.whatsapp_extract import (
    MAX_EXTRACTIONS_PER_24H,
    _extractions_in_current_window,  # aynı 5/24s bütçesi paylaşılır (bilinçli)
)
from app.core.ai_limits import MAX_TOKENS_CONVERSATION_SUMMARY
from app.core.config import settings
from app.models.lead import Lead

MODEL_NAME = "gemini-2.5-flash"

# LLM özetine ancak konuşma bu kadar mesajı geçtiyse başvurulur — kısa
# konuşmada özetlenecek bağlam yoktur, son mesaj zaten prompt'a giriyor.
LLM_SUMMARY_MIN_MESSAGES = 6
# Önbellekli LLM özeti bu süre boyunca taze sayılır, yeniden üretilmez.
LLM_SUMMARY_TTL = timedelta(hours=24)

SUMMARY_PROMPT_TEMPLATE = """Aşağıda bir emlak ofisine WhatsApp'tan yazan bir adayın son mesajları var. \
Adayın ne aradığını TEK bir kısa Türkçe cümleyle özetle (örn. "Müşteri Nilüfer'de 20.000 TL'ye \
3+1 kiralık arıyor"). SADECE bu cümleyi yaz — açıklama, selamlama, markdown ekleme.

Mesajlar:
{messages}"""

_LISTING_TYPE_LABELS = {"sale": "satılık", "rent": "kiralık"}
_PROPERTY_TYPE_LABELS = {"residential": "konut", "commercial": "iş yeri", "land": "arsa"}


class LeadSummaryError(Exception):
    """Konuşma özeti üretilemedi (yapılandırma eksik, LLM hatası)."""


def _format_try(amount: float) -> str:
    return f"{amount:,.0f} TL".replace(",", ".")


def build_structured_summary(lead: Lead) -> str | None:
    """Yapısal alanlardan deterministik tek cümle; hiçbir alan dolu değilse
    None (çağıran taraf LLM fallback'ine bakar). Gemini'ye gitmez."""
    parts: list[str] = []
    if lead.district:
        parts.append(f"{lead.district}'de")
    if lead.budget_max:
        parts.append(f"{_format_try(float(lead.budget_max))}'ye kadar")
    if lead.room_count:
        parts.append(lead.room_count)
    if lead.listing_type_preference:
        parts.append(_LISTING_TYPE_LABELS.get(lead.listing_type_preference, lead.listing_type_preference))
    if lead.property_type_preference:
        parts.append(_PROPERTY_TYPE_LABELS.get(lead.property_type_preference, lead.property_type_preference))
    if not parts:
        return None
    return f"Müşteri {' '.join(parts)} arıyor."


def should_generate_llm_summary(lead: Lead, now: datetime | None = None) -> bool:
    """LLM özet fallback'inin maliyet kapısı: yapısal özet yoksa VE konuşma
    uzunsa VE taze bir önbellek yoksa VE extraction'ın 5/24s bütçesinde yer
    varsa True. (Otomatik webhook akışı bunu HİÇ çağırmaz — sadece danışmanın
    panelden tetiklediği "AI ile Yanıt Öner" akışı.)"""
    now = now or datetime.now(timezone.utc)
    if build_structured_summary(lead) is not None:
        return False
    if (lead.message_count or 0) < LLM_SUMMARY_MIN_MESSAGES:
        return False
    if lead.conversation_summary and lead.conversation_summary_at:
        if now - lead.conversation_summary_at < LLM_SUMMARY_TTL:
            return False  # taze önbellek var, yeniden üretme
    used = _extractions_in_current_window(lead.llm_extraction_count, lead.last_llm_extraction_at, now)
    return used < MAX_EXTRACTIONS_PER_24H


def summarize_conversation(messages: list[str]) -> str:
    """Son mesajları (kayan pencere — çağıran taraf sınırlar, tüm geçmiş asla
    gelmez) Gemini ile tek cümleye sıkıştırır. Çağıran taraf sonucu
    leads.conversation_summary'ye önbellekler ve extraction sayaçlarını işletir
    (compute_new_extraction_counters — maliyet oluştu)."""
    if not settings.gemini_api_key:
        raise LeadSummaryError("__not_configured__")
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(MODEL_NAME)

    prompt = SUMMARY_PROMPT_TEMPLATE.format(messages="\n".join(f"- {m}" for m in messages))
    try:
        response = model.generate_content(
            prompt, generation_config={"max_output_tokens": MAX_TOKENS_CONVERSATION_SUMMARY}
        )
    except Exception as exc:  # Gemini SDK'sı tek bir ortak hata tipi sağlamıyor
        raise LeadSummaryError(f"Konuşma özeti üretilemedi: {exc}") from exc

    text = getattr(response, "text", None)
    if not text:
        raise LeadSummaryError("Modelden yanıt alınamadı, tekrar deneyin.")
    return text.strip()


def fresh_cached_summary(lead: Lead, now: datetime | None = None) -> str | None:
    """Taze (TTL içindeki) önbellekli LLM özeti varsa döner."""
    now = now or datetime.now(timezone.utc)
    if lead.conversation_summary and lead.conversation_summary_at:
        if now - lead.conversation_summary_at < LLM_SUMMARY_TTL:
            return lead.conversation_summary
    return None
