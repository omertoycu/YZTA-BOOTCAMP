import google.generativeai as genai

from app.core.config import settings

MODEL_NAME = "gemini-2.5-flash"

PROMPT_TEMPLATE = """Sen bir emlak ofisinin WhatsApp asistanısın. Bir adaya kısa, \
samimi ve profesyonel bir Türkçe WhatsApp yanıtı taslağı yazacaksın.

Adayın son mesajı: "{last_message}"
Adayın aradığı kriterler: bölge={district}, oda={room_count}, bütçe üst sınırı={budget_max}

Aşağıda adayın kriterlerine uyan, ofisin GERÇEK aktif portföyleri var. SADECE bu \
listedeki ilanlardan bahset, ASLA var olmayan bir ilan uydurma. Liste boşsa uygun \
ilan olmadığını nazikçe belirt, yakında haber vereceğini söyle.

Portföyler:
{listings_block}

SADECE taslak mesaj metnini yaz — açıklama, markdown ya da JSON ekleme, düz metin."""


class ReplyDraftError(Exception):
    """Yanıt taslağı üretilemedi (yapılandırma eksik, LLM hatası)."""


def _get_model() -> "genai.GenerativeModel":
    if not settings.gemini_api_key:
        raise ReplyDraftError("__not_configured__")
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(MODEL_NAME)


def _format_try(amount: float) -> str:
    return f"{amount:,.0f} TL".replace(",", ".")


def draft_reply(
    *,
    last_message: str | None,
    district: str | None,
    room_count: str | None,
    budget_max: float | None,
    candidate_listings: list[dict],
) -> str:
    """RAG'ın generation adımı: retrieval (Matching Agent'ın döndürdüğü gerçek/
    canlı portföyler, bkz. app/api/routes/leads.py: suggest_reply) burada
    Gemini'ye grounding context olarak verilir. Hiçbir zaman otomatik göndermez
    — sadece taslak metin döner, çağıran route (POST /leads/{id}/suggest-reply)
    danışman onayına sunar."""
    model = _get_model()
    listings_block = (
        "\n".join(f"- {c['title']} — {_format_try(c['price'])}" for c in candidate_listings)
        if candidate_listings
        else "(uygun portföy yok)"
    )
    prompt = PROMPT_TEMPLATE.format(
        last_message=last_message or "(mesaj yok)",
        district=district or "belirtilmedi",
        room_count=room_count or "belirtilmedi",
        budget_max=_format_try(budget_max) if budget_max else "belirtilmedi",
        listings_block=listings_block,
    )
    try:
        response = model.generate_content(prompt)  # düz metin — JSON mime type gerekmez
    except Exception as exc:  # Gemini SDK'sı tek bir ortak hata tipi sağlamıyor
        raise ReplyDraftError(f"Yanıt taslağı üretilemedi: {exc}") from exc

    text = getattr(response, "text", None)
    if not text:
        raise ReplyDraftError("Modelden yanıt alınamadı, tekrar deneyin.")
    return text.strip()
