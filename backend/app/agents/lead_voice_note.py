import json
import re
from datetime import date, datetime, timezone

import google.generativeai as genai

from app.core.ai_limits import MAX_TOKENS_VOICE
from app.core.config import settings

MODEL_NAME = "gemini-2.5-flash"

# bkz. app/api/routes/leads.py: LEAD_STATUSES — tek kaynak orada, burada sadece
# modelin geçerli bir değer seçmesi/doğrulanması için elle tutuluyor.
LEAD_STATUS_CHOICES = ("new", "contacted", "viewing", "negotiation", "won", "lost")

WEEKDAY_NAMES_TR = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")

PROMPT_TEMPLATE = """Bu ses kaydı, bir emlak danışmanının bir aday (potansiyel müşteri) ile yaptığı \
görüşme sonrası sözlü olarak tuttuğu bir not/özettir (örn. "Ahmet bey daireyi beğendi ama fiyatı \
yüksek buldu, cuma günü tekrar arayacağım"). Bugünün tarihi {today} ({today_weekday}). Kaydı dinle \
ve SADECE aşağıdaki JSON şemasına uygun, başka hiçbir metin içermeyen bir yanıt üret:

{{
  "transcript": "<sesin birebir Türkçe transkripti>",
  "note_summary": "<görüşmenin CRM notu formatında kısa özeti, 1-3 cümle, yoksa null>",
  "suggested_status": "<konuşmadan adayın satış hunisindeki aşaması net anlaşılıyorsa şunlardan biri: {statuses}; net değilse null>",
  "reminder_date": "<bir sonraki temas için bahsedilen gün/tarih varsa, bugünün tarihine göre hesaplanmış YYYY-MM-DD; yoksa null>",
  "reminder_note": "<hatırlatmanın kısa açıklaması, örn. 'Fiyat konusunda tekrar ara'; reminder_date null ise bu da null>"
}}

Emin olmadığın alanları null bırak, tahmin yapma. Yanıtın geçerli JSON olmalı, markdown kod bloğu \
(```) kullanma."""


class VoiceNoteError(Exception):
    """Ses işlenemedi (yapılandırma eksik, LLM hatası, geçersiz yanıt)."""


def _get_model() -> "genai.GenerativeModel":
    if not settings.gemini_api_key:
        raise VoiceNoteError("__not_configured__")
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(MODEL_NAME)


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise VoiceNoteError("Model yanıtı ayrıştırılamadı, tekrar deneyin.") from exc


def _parse_reminder_date(value: object) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d")
    except ValueError:
        return None
    return parsed.replace(hour=9, tzinfo=timezone.utc)


def transcribe_and_extract_note(audio_bytes: bytes, content_type: str, today: date | None = None) -> dict:
    """Danışmanın bir aday hakkında bıraktığı sesli notu Gemini'nin native audio
    girişine gönderir; transkript + görüşme notu özeti + önerilen pipeline durumu +
    hatırlatma taslağı döner. Hiçbir şey otomatik yazılmaz — çağıran taraf (route)
    danışman onayına kadar sadece taslak olarak kullanır."""
    model = _get_model()
    today = today or datetime.now(timezone.utc).date()
    prompt = PROMPT_TEMPLATE.format(
        today=today.isoformat(),
        today_weekday=WEEKDAY_NAMES_TR[today.weekday()],
        statuses=", ".join(LEAD_STATUS_CHOICES),
    )

    try:
        response = model.generate_content(
            [{"mime_type": content_type, "data": audio_bytes}, prompt],
            generation_config={
                "response_mime_type": "application/json",
                "max_output_tokens": MAX_TOKENS_VOICE,
            },
        )
    except Exception as exc:  # Gemini SDK'sı tek bir ortak hata tipi sağlamıyor
        raise VoiceNoteError(f"Ses işlenemedi: {exc}") from exc

    text = getattr(response, "text", None)
    if not text:
        raise VoiceNoteError("Modelden yanıt alınamadı, tekrar deneyin.")

    data = _parse_json_response(text)
    suggested_status = data.get("suggested_status")
    if suggested_status not in LEAD_STATUS_CHOICES:
        suggested_status = None

    return {
        "transcript": data.get("transcript") or "",
        "note_summary": data.get("note_summary"),
        "suggested_status": suggested_status,
        "reminder_at": _parse_reminder_date(data.get("reminder_date")),
        "reminder_note": data.get("reminder_note"),
    }
