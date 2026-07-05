import hashlib
import hmac
import json

from sqlalchemy import select

from app.agents import intake
from app.core.config import settings
from app.models.office import Office

WHATSAPP_APP_SECRET = "test-whatsapp-secret"


def _register_office(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "supersecret123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _set_phone_number_id(db_session, office_name, phone_number_id, notification_phone=None):
    office = db_session.execute(select(Office).where(Office.name == office_name)).scalar_one()
    office.whatsapp_phone_number_id = phone_number_id
    if notification_phone:
        office.notification_phone = notification_phone
    db_session.commit()


def _build_payload(phone_number_id, message_id, contact_phone):
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": phone_number_id},
                            "messages": [
                                {
                                    "id": message_id,
                                    "from": contact_phone,
                                    "type": "text",
                                    "text": {"body": "Merhaba, ilgileniyorum"},
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    }


def _sign(body: bytes) -> str:
    digest = hmac.new(WHATSAPP_APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _post_webhook(client, payload):
    body = json.dumps(payload).encode()
    return client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": _sign(body)},
    )


def test_webhook_verification_handshake(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_verify_token", "verify-me")
    resp = client.get(
        "/webhooks/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "12345"},
    )
    assert resp.status_code == 200
    assert resp.text == "12345"


def test_webhook_verification_rejects_wrong_token(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_verify_token", "verify-me")
    resp = client.get(
        "/webhooks/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "12345"},
    )
    assert resp.status_code == 403


def test_inbound_message_creates_lead(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", WHATSAPP_APP_SECRET)
    headers = _register_office(client, "Ofis Intake Test 1", "owner1@intake-test.com")
    _set_phone_number_id(db_session, "Ofis Intake Test 1", "1000000001")

    resp = _post_webhook(client, _build_payload("1000000001", "wamid.AAA", "905551110001"))
    assert resp.status_code == 200

    leads = client.get("/leads", headers=headers).json()
    assert len(leads) == 1
    assert leads[0]["contact_phone"] == "905551110001"
    assert leads[0]["source"] == "whatsapp"
    assert leads[0]["message_count"] == 1
    assert leads[0]["last_contacted_at"] is not None


def test_new_lead_notifies_office_notification_phone(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", WHATSAPP_APP_SECRET)
    headers = _register_office(client, "Ofis Intake Notify 1", "owner@intake-notify-1.com")
    _set_phone_number_id(db_session, "Ofis Intake Notify 1", "1000000010", notification_phone="905559990010")

    sent_calls = []
    monkeypatch.setattr(
        intake,
        "send_whatsapp_text",
        lambda phone_number_id, to, text: sent_calls.append((phone_number_id, to, text)),
    )

    resp = _post_webhook(client, _build_payload("1000000010", "wamid.NOTIFY1", "905551119999"))
    assert resp.status_code == 200
    assert len(sent_calls) == 1
    assert sent_calls[0][0] == "1000000010"
    assert sent_calls[0][1] == "905559990010"
    assert "905551119999" in sent_calls[0][2]

    # İkinci mesaj (var olan lead güncelleniyor) tekrar bildirim GÖNDERMEMELİ.
    _post_webhook(client, _build_payload("1000000010", "wamid.NOTIFY2", "905551119999"))
    assert len(sent_calls) == 1

    leads = client.get("/leads", headers=headers).json()
    assert len(leads) == 1
    assert leads[0]["message_count"] == 2


def test_new_lead_without_notification_phone_does_not_attempt_send(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", WHATSAPP_APP_SECRET)
    _register_office(client, "Ofis Intake Notify 2", "owner@intake-notify-2.com")
    _set_phone_number_id(db_session, "Ofis Intake Notify 2", "1000000011")  # notification_phone yok

    sent_calls = []
    monkeypatch.setattr(
        intake, "send_whatsapp_text", lambda *args: sent_calls.append(args)
    )

    resp = _post_webhook(client, _build_payload("1000000011", "wamid.NOTIFY3", "905551119998"))
    assert resp.status_code == 200
    assert sent_calls == []


def test_second_message_increments_existing_lead(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", WHATSAPP_APP_SECRET)
    headers = _register_office(client, "Ofis Intake Test 2", "owner2@intake-test.com")
    _set_phone_number_id(db_session, "Ofis Intake Test 2", "1000000002")

    _post_webhook(client, _build_payload("1000000002", "wamid.BBB1", "905551110002"))
    _post_webhook(client, _build_payload("1000000002", "wamid.BBB2", "905551110002"))

    leads = client.get("/leads", headers=headers).json()
    assert len(leads) == 1
    assert leads[0]["message_count"] == 2


def test_duplicate_message_id_is_not_double_counted(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", WHATSAPP_APP_SECRET)
    headers = _register_office(client, "Ofis Intake Test 3", "owner3@intake-test.com")
    _set_phone_number_id(db_session, "Ofis Intake Test 3", "1000000003")

    payload = _build_payload("1000000003", "wamid.CCC", "905551110003")
    _post_webhook(client, payload)
    _post_webhook(client, payload)  # Meta'nın retry'ı: aynı mesaj id'si tekrar geliyor

    leads = client.get("/leads", headers=headers).json()
    assert len(leads) == 1
    assert leads[0]["message_count"] == 1


def test_invalid_signature_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", WHATSAPP_APP_SECRET)
    body = json.dumps(_build_payload("9999999999", "wamid.DDD", "905551110004")).encode()
    resp = client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": "sha256=deadbeef"},
    )
    assert resp.status_code == 401


def test_signature_required_in_production_when_no_app_secret_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", None)
    monkeypatch.setattr(settings, "environment", "production")

    body = json.dumps(_build_payload("1000000007", "wamid.GGG", "905551110007")).encode()
    resp = client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 401


def test_unknown_phone_number_id_is_ignored_but_returns_200(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", WHATSAPP_APP_SECRET)
    resp = _post_webhook(client, _build_payload("does-not-exist", "wamid.EEE", "905551110005"))
    assert resp.status_code == 200


def test_signature_check_skipped_when_no_app_secret_configured(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", None)
    headers = _register_office(client, "Ofis Intake Test 4", "owner4@intake-test.com")
    _set_phone_number_id(db_session, "Ofis Intake Test 4", "1000000006")

    body = json.dumps(_build_payload("1000000006", "wamid.FFF", "905551110006")).encode()
    resp = client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200

    leads = client.get("/leads", headers=headers).json()
    assert len(leads) == 1
