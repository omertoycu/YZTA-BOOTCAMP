import httpx

from app.core.config import settings
from app.core.http import get_http_client

GRAPH_API_VERSION = "v21.0"


class WhatsAppSendError(Exception):
    """Mesaj gönderilemedi (yapılandırma eksik, Meta API hatası)."""


def _describe_meta_error(exc: httpx.HTTPStatusError) -> str:
    """Meta'nın gerçek hata mesajını (ör. "24 saat penceresi doldu", "alıcı
    numara onaylı değil") kullanıcıya yansıtır — sadece durum koduyla
    ("Meta hata döndürdü (durum kodu 400)") danışman ne yapması gerektiğini
    hiç anlayamıyordu. Token hataları (code 190 / OAuthException) için ayrıca
    ne YAPILACAĞI da söylenir: Meta'nın geçici token'ları ~24 saatte doluyor,
    danışmanın gördüğü çıplak "Authentication Error" hiçbir yol göstermiyordu
    (gerçek prod şikayeti). Meta'nın yanıtı JSON değilse/beklenen şekilde
    değilse eski genel mesaja düşülür."""
    try:
        error = exc.response.json().get("error", {})
        detail = error.get("message")
        code = error.get("code")
    except (ValueError, AttributeError):
        detail = None
        code = None
    if code == 190 or (detail and "authentication" in detail.lower()):
        return (
            "WhatsApp erişim token'ı geçersiz veya süresi dolmuş. Meta'nın geçici "
            "token'ları ~24 saatte dolar — Meta for Developers'tan yeni bir token alıp "
            "Railway'deki WHATSAPP_TOKEN değişkenini güncelleyin (kalıcı çözüm: System "
            "User üzerinden süresiz token)."
        )
    if detail:
        return f"Meta hata döndürdü: {detail}"
    return f"Meta hata döndürdü (durum kodu {exc.response.status_code})."


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
        raise WhatsAppSendError(_describe_meta_error(exc)) from exc
    except httpx.RequestError as exc:
        raise WhatsAppSendError("WhatsApp'a mesaj gönderilemedi, tekrar deneyin.") from exc
