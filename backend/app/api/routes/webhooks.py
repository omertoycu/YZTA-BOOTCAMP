import hashlib
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.agents.intake import UnknownWhatsAppRecipientError, process_inbound_message, resolve_office_id
from app.core.config import settings
from app.core.db import get_db

router = APIRouter(prefix="/webhooks/whatsapp", tags=["webhooks"])


@router.get("")
def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    """Meta'nın webhook kurulum handshake'i — Business Manager'da webhook URL'i
    kaydedilirken Meta bu endpoint'e GET atar, doğru token'ı görünce challenge'ı
    aynen geri döndürmemiz gerekir."""
    if hub_mode == "subscribe" and hub_verify_token and hub_verify_token == settings.whatsapp_verify_token:
        return PlainTextResponse(hub_challenge or "")
    raise HTTPException(status_code=403, detail="Doğrulama başarısız")


def _verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    if not settings.whatsapp_app_secret:
        if settings.environment == "production":
            # Prod'da app secret'sız webhook'a asla güvenilmez: yanlışlıkla secret
            # set edilmeden deploy edilmişse endpoint sessizce açık kalmak yerine kapanır.
            return False
        # Meta onayı/app secret'ı henüz yoksa (dev/mock aşaması) imza kontrolü atlanır.
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(settings.whatsapp_app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)


@router.post("")
async def receive_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: str | None = Header(default=None),
):
    raw_body = await request.body()
    if not _verify_signature(raw_body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Geçersiz imza")

    payload = await request.json()

    # Meta'ya her zaman hızlıca 200 dönmeliyiz — aksi halde tekrar tekrar retry
    # eder ve çok sayıda hata birikince webhook'u otomatik devre dışı bırakabilir.
    # Bilinmeyen bir alıcı/format sessizce yoksayılır, işlemi durdurmaz.
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id")
            for message in value.get("messages", []):
                contact_phone = message.get("from")
                external_message_id = message.get("id")
                if not phone_number_id or not contact_phone or not external_message_id:
                    continue
                try:
                    office_id = resolve_office_id(db, phone_number_id)
                except UnknownWhatsAppRecipientError:
                    continue
                process_inbound_message(
                    db,
                    office_id=office_id,
                    external_message_id=external_message_id,
                    contact_phone=contact_phone,
                )

    return {"status": "received"}
