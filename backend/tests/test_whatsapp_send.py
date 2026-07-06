import httpx
import pytest
from sqlalchemy import select

from app.agents import whatsapp_send
from app.agents.whatsapp_send import WhatsAppSendError, send_whatsapp_text
from app.api.routes import leads as leads_route
from app.core.config import settings
from app.models.office import Office


def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "Supersecret123!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_lead(client, headers, district="Kadıköy"):
    resp = client.post(
        "/leads",
        json={"contact_phone": "905551112233", "district": district},
        headers=headers,
    )
    return resp.json()["id"]


def _set_phone_number_id(db_session, office_name, phone_number_id):
    office = db_session.execute(select(Office).where(Office.name == office_name)).scalar_one()
    office.whatsapp_phone_number_id = phone_number_id
    db_session.commit()


def test_follow_up_requires_auth(client):
    resp = client.post("/leads/does-not-exist/follow-up", json={})
    assert resp.status_code == 401


def test_follow_up_returns_503_when_office_has_no_whatsapp_number(client):
    headers = _register(client, "Ofis FollowUp Test 1", "owner1@followup-test.com")
    lead_id = _create_lead(client, headers)

    resp = client.post(f"/leads/{lead_id}/follow-up", json={}, headers=headers)
    assert resp.status_code == 503


def test_follow_up_sends_default_template(client, db_session, monkeypatch):
    headers = _register(client, "Ofis FollowUp Test 2", "owner2@followup-test.com")
    _set_phone_number_id(db_session, "Ofis FollowUp Test 2", "1000000010")
    lead_id = _create_lead(client, headers, district="Beşiktaş")

    sent_calls = []
    monkeypatch.setattr(
        leads_route,
        "send_whatsapp_text",
        lambda phone_number_id, to, text: sent_calls.append((phone_number_id, to, text)),
    )

    resp = client.post(f"/leads/{lead_id}/follow-up", json={}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["sent"] is True
    assert "Beşiktaş" in body["message"]
    assert len(sent_calls) == 1
    assert sent_calls[0][0] == "1000000010"
    assert sent_calls[0][1] == "905551112233"


def test_follow_up_works_with_no_request_body(client, db_session, monkeypatch):
    """Regresyon testi: frontend'in "Takip Mesajı Gönder" butonu hiç body
    göndermiyor (bkz. app/leads/page.tsx: apiFetch(..., { method: "POST" })).
    payload'un varsayılanı olmadan FastAPI, body tamamen eksikken WhatsApp
    bağlantı kontrolüne hiç ulaşmadan 422 "Field required" döndürüyordu —
    yani bu buton hiçbir zaman gerçek bir isteği tamamlayamıyordu."""
    headers = _register(client, "Ofis FollowUp Test 4", "owner4@followup-test.com")
    _set_phone_number_id(db_session, "Ofis FollowUp Test 4", "1000000012")
    lead_id = _create_lead(client, headers, district="Üsküdar")

    sent_calls = []
    monkeypatch.setattr(
        leads_route,
        "send_whatsapp_text",
        lambda phone_number_id, to, text: sent_calls.append((phone_number_id, to, text)),
    )

    resp = client.post(f"/leads/{lead_id}/follow-up", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["sent"] is True
    assert len(sent_calls) == 1


def test_follow_up_returns_502_on_send_failure(client, db_session, monkeypatch):
    headers = _register(client, "Ofis FollowUp Test 3", "owner3@followup-test.com")
    _set_phone_number_id(db_session, "Ofis FollowUp Test 3", "1000000011")
    lead_id = _create_lead(client, headers)

    def _raise(phone_number_id, to, text):
        raise whatsapp_send.WhatsAppSendError("Meta hata döndürdü (durum kodu 500).")

    monkeypatch.setattr(leads_route, "send_whatsapp_text", _raise)

    resp = client.post(f"/leads/{lead_id}/follow-up", json={}, headers=headers)
    assert resp.status_code == 502


class _FakeMetaResponse:
    """httpx.Response'ı taklit eder — send_whatsapp_text'in Meta hata body'sini
    okuyup okuyamadığını (_describe_meta_error) gerçek bir ağ isteği atmadan
    test etmek için."""

    def __init__(self, status_code: int, payload: dict | None = None, is_json: bool = True):
        self.status_code = status_code
        self._payload = payload
        self._is_json = is_json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        if not self._is_json:
            raise ValueError("not json")
        return self._payload


class _FakeHttpClient:
    def __init__(self, response: _FakeMetaResponse):
        self._response = response

    def post(self, url, headers=None, json=None):
        return self._response

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_send_whatsapp_text_raises_not_configured_without_token(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_token", None)
    with pytest.raises(WhatsAppSendError, match="__not_configured__"):
        send_whatsapp_text("123", "905551234567", "merhaba")


def test_send_whatsapp_text_surfaces_meta_error_message(monkeypatch):
    """Regresyon testi: canlıda Takip Mesajı Gönder 502 verdiğinde danışman
    sadece "Meta hata döndürdü (durum kodu 400)." görüyordu, asıl sebep
    (ör. 24 saatlik mesajlaşma penceresi doldu) hiç yansımıyordu."""
    monkeypatch.setattr(settings, "whatsapp_token", "fake-token")
    response = _FakeMetaResponse(
        400,
        {
            "error": {
                "message": "(#131047) Message failed to send because more than 24 hours "
                "have passed since the customer last replied to this number.",
                "code": 131047,
            }
        },
    )
    monkeypatch.setattr(whatsapp_send, "get_http_client", lambda: _FakeHttpClient(response))

    with pytest.raises(WhatsAppSendError, match="24 hours"):
        send_whatsapp_text("123", "905551234567", "merhaba")


def test_send_whatsapp_text_falls_back_to_status_code_when_body_not_json(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_token", "fake-token")
    response = _FakeMetaResponse(500, is_json=False)
    monkeypatch.setattr(whatsapp_send, "get_http_client", lambda: _FakeHttpClient(response))

    with pytest.raises(WhatsAppSendError, match="durum kodu 500"):
        send_whatsapp_text("123", "905551234567", "merhaba")


def test_send_whatsapp_text_explains_expired_token(monkeypatch):
    """Gerçek prod şikayeti: Meta'nın geçici token'ı dolunca danışman sadece
    çıplak "Authentication Error" görüyordu — artık ne YAPILACAĞI da
    söylenmeli (WHATSAPP_TOKEN'ı yenile, System User kalıcı token önerisi)."""
    monkeypatch.setattr(settings, "whatsapp_token", "expired-token")
    response = _FakeMetaResponse(
        401,
        {"error": {"message": "Error validating access token: Session has expired", "code": 190}},
    )
    monkeypatch.setattr(whatsapp_send, "get_http_client", lambda: _FakeHttpClient(response))

    with pytest.raises(WhatsAppSendError, match="WHATSAPP_TOKEN"):
        send_whatsapp_text("123", "905551234567", "merhaba")
