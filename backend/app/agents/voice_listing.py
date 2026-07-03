import json
import re

import google.generativeai as genai

from app.core.config import settings

MODEL_NAME = "gemini-2.5-flash"

SUPPORTED_AUDIO_TYPES = {
    "audio/wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/aac",
    "audio/ogg",
    "audio/webm",
    "audio/flac",
    "audio/x-aiff",
    "audio/aiff",
    "audio/mp4",
    "audio/m4a",
}

MAX_AUDIO_BYTES = 20 * 1024 * 1024  # 20MB, birkaç dakikalık sesli not için yeterli

PROMPT = """Bu ses kaydı, bir emlak danışmanının bir gayrimenkul portföyü hakkında \
sözlü olarak verdiği bilgilerdir (örn. "3+1, 120 metrekare, Kadıköy'de, 8 milyon TL, \
asansörlü, otoparklı bir daire"). Kaydı dinle ve SADECE aşağıdaki JSON şemasına uygun, \
başka hiçbir metin içermeyen bir yanıt üret:

{
  "transcript": "<sesin birebir Türkçe transkripti>",
  "title": "<kısa, çekici bir ilan başlığı, yoksa null>",
  "district": "<bahsedilen mahalle/ilçe, yoksa null>",
  "price": <sayı olarak TL fiyatı, yoksa null>,
  "room_count": "<örn. '3+1', yoksa null>",
  "square_meters": <sayı olarak metrekare, yoksa null>
}

Emin olmadığın alanları null bırak, tahmin yapma. Yanıtın geçerli JSON olmalı, \
markdown kod bloğu (```) kullanma."""


class VoiceListingError(Exception):
    """Ses işlenemedi (yapılandırma eksik, LLM hatası, geçersiz yanıt)."""


def _get_model() -> "genai.GenerativeModel":
    if not settings.gemini_api_key:
        raise VoiceListingError("__not_configured__")
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(MODEL_NAME)


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise VoiceListingError("Model yanıtı ayrıştırılamadı, tekrar deneyin.") from exc


def transcribe_and_extract(audio_bytes: bytes, content_type: str) -> dict:
    """Ses kaydını Gemini'nin native audio girişine gönderir, transkript +
    yapılandırılmış ilan taslağı döner. Hiçbir alan otomatik yayınlanmaz —
    çağıran taraf (route) danışman onayına kadar sadece taslak olarak kullanır."""
    model = _get_model()

    try:
        response = model.generate_content(
            [{"mime_type": content_type, "data": audio_bytes}, PROMPT],
            generation_config={"response_mime_type": "application/json"},
        )
    except Exception as exc:  # Gemini SDK'sı tek bir ortak hata tipi sağlamıyor
        raise VoiceListingError(f"Ses işlenemedi: {exc}") from exc

    text = getattr(response, "text", None)
    if not text:
        raise VoiceListingError("Modelden yanıt alınamadı, tekrar deneyin.")

    data = _parse_json_response(text)
    return {
        "transcript": data.get("transcript") or "",
        "title": data.get("title"),
        "district": data.get("district"),
        "price": data.get("price"),
        "room_count": data.get("room_count"),
        "square_meters": data.get("square_meters"),
    }
