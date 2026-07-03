import httpx

from app.core.config import settings
from app.core.http import get_http_client

GRAPH_API_VERSION = "v21.0"


class WhatsAppSendError(Exception):
    """Mesaj gönderilemedi (yapılandırma eksik, Meta API hatası)."""


def send_whatsapp_text(phone_number_id: str, to: str, text: str) -> None:
    """Meta WhatsApp Cloud API üzerinden serbest metin mesaj gönderir.

    Not: Meta, son kullanıcı mesajından 24 saat sonra sadece önceden onaylı
    şablon (template) mesajlarına izin veriyor; bu fonksiyon basit metin
    gönderir. Bir Meta test numarasıyla (Business doğrulaması bitmeden) demo
    amaçlı test alıcılarına göndermek için yeterli — 24 saat penceresi dışına
    düşen gerçek prod takip mesajları için ayrıca onaylı bir şablon kaydı
    gerekir, bu MVP kapsamı dışında.
    """
    if not settings.whatsapp_token:
        raise WhatsAppSendError("__not_configured__")

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/messages"
    try:
        with get_http_client() as client:
            response = client.post(
                url,
                headers={"Authorization": f"Bearer {settings.whatsapp_token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "text",
                    "text": {"body": text},
                },
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise WhatsAppSendError(f"Meta hata döndürdü (durum kodu {exc.response.status_code}).") from exc
    except httpx.RequestError as exc:
        raise WhatsAppSendError("WhatsApp'a mesaj gönderilemedi, tekrar deneyin.") from exc
