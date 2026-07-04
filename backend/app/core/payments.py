"""iyzico Checkout Form (CF) entegrasyonu — resmi Python SDK'sı yerine doğrudan
HTTP + IYZWSv2 imzası kullanılır (SDK eski ve bakımsız; imza şeması ~40 satır).

Akış: initialize_checkout_form → danışman iyzico'nun barındırdığı ödeme
sayfasına yönlendirilir → iyzico callbackUrl'e (POST /billing/callback) token
POST'lar → retrieve_checkout_result ile sonuç iyzico'dan doğrulanır (token
istemciden gelse bile ödeme durumu her zaman iyzico API'sinden okunur, asla
istemci beyanına güvenilmez).

Sandbox/prod ayrımı sadece IYZICO_BASE_URL ile yapılır — kod aynı.
"""
import base64
import hashlib
import hmac
import json
import uuid

import httpx

from app.core.config import settings
from app.core.http import get_http_client


class IyzicoError(Exception):
    """iyzico isteği başarısız (yapılandırma eksik, API hatası)."""


def _auth_header(uri_path: str, request_body: str) -> str:
    """IYZWSv2 imzası: HMAC-SHA256(randomKey + uriPath + body, secretKey)."""
    random_key = uuid.uuid4().hex
    signature = hmac.new(
        settings.iyzico_secret_key.encode(),
        (random_key + uri_path + request_body).encode(),
        hashlib.sha256,
    ).hexdigest()
    authorization = (
        f"apiKey:{settings.iyzico_api_key}&randomKey:{random_key}&signature:{signature}"
    )
    return "IYZWSv2 " + base64.b64encode(authorization.encode()).decode()


def _post(uri_path: str, payload: dict) -> dict:
    if not settings.iyzico_api_key or not settings.iyzico_secret_key:
        raise IyzicoError("__not_configured__")

    # İmza istek gövdesinin birebir string'i üzerinden hesaplandığı için gövde
    # bir kez serialize edilir ve aynı string gönderilir (json= kullanılmaz).
    body = json.dumps(payload)
    try:
        with get_http_client() as client:
            response = client.post(
                settings.iyzico_base_url + uri_path,
                content=body,
                headers={
                    "Authorization": _auth_header(uri_path, body),
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise IyzicoError(f"iyzico hata döndürdü (durum kodu {exc.response.status_code}).") from exc
    except httpx.RequestError as exc:
        raise IyzicoError("iyzico'ya ulaşılamadı, tekrar deneyin.") from exc

    data = response.json()
    if data.get("status") != "success":
        raise IyzicoError(data.get("errorMessage") or "iyzico isteği başarısız oldu.")
    return data


def initialize_checkout_form(
    *,
    office_id: str,
    plan_id: str,
    plan_name: str,
    monthly_price: str,
    buyer_email: str,
    buyer_name: str,
    callback_url: str,
) -> dict:
    """Ödeme sayfasını başlatır; {token, payment_page_url} döner.

    conversationId'ye office_id:plan_id gömülür — callback'te hangi ofisin
    hangi plana geçtiği iyzico'nun doğruladığı yanıttan okunur (istemciden değil).
    """
    # iyzico buyer/adres alanlarını zorunlu tutar; abonelik ürününde fiziksel
    # teslimat olmadığı için sandbox/MVP'de jenerik değerler yeterli.
    address = {
        "contactName": buyer_name,
        "city": "Istanbul",
        "country": "Turkey",
        "address": "Dijital teslimat — PortföyAI aboneliği",
    }
    payload = {
        "locale": "tr",
        "conversationId": f"{office_id}:{plan_id}",
        "price": monthly_price,
        "paidPrice": monthly_price,
        "currency": "TRY",
        "basketId": plan_id,
        "paymentGroup": "SUBSCRIPTION",
        "callbackUrl": callback_url,
        "buyer": {
            "id": office_id,
            "name": buyer_name,
            "surname": "-",
            "email": buyer_email,
            "identityNumber": "11111111111",  # sandbox zorunlu alanı; canlıda gerçek TCKN/VKN istenecek
            "registrationAddress": address["address"],
            "ip": "85.34.78.112",
            "city": address["city"],
            "country": address["country"],
        },
        "billingAddress": address,
        "shippingAddress": address,
        "basketItems": [
            {
                "id": plan_id,
                "name": f"PortföyAI {plan_name} Aboneliği (aylık)",
                "category1": "Abonelik",
                "itemType": "VIRTUAL",
                "price": monthly_price,
            }
        ],
    }
    data = _post("/payment/iyzipos/checkoutform/initialize/auth/ecom", payload)
    return {"token": data["token"], "payment_page_url": data["paymentPageUrl"]}


def retrieve_checkout_result(token: str) -> dict:
    """Callback token'ının gerçek sonucunu iyzico'dan okur.

    {paid: bool, office_id, plan_id} döner — office_id/plan_id iyzico'nun
    sakladığı conversationId'den gelir, istemcinin gönderdiği hiçbir değere
    güvenilmez.
    """
    data = _post(
        "/payment/iyzipos/checkoutform/auth/ecom/detail",
        {"locale": "tr", "token": token},
    )
    conversation_id = data.get("conversationId") or ""
    office_id, _, plan_id = conversation_id.partition(":")
    return {
        "paid": data.get("paymentStatus") == "SUCCESS",
        "office_id": office_id or None,
        "plan_id": plan_id or None,
    }
