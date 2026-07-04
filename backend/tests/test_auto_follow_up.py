from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.agents import follow_up, whatsapp_send
from app.agents.follow_up import FOLLOW_UP_CHAIN
from app.agents.intake import process_inbound_message
from app.core.config import settings
from app.models.lead import Lead
from app.models.office import Office


def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "supersecret123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_lead(client, headers, district="Kadıköy", phone="905551112233"):
    resp = client.post(
        "/leads",
        json={"contact_phone": phone, "district": district},
        headers=headers,
    )
    return resp.json()["id"]


def _set_phone_number_id(db_session, office_name, phone_number_id):
    office = db_session.execute(select(Office).where(Office.name == office_name)).scalar_one()
    office.whatsapp_phone_number_id = phone_number_id
    db_session.commit()
    return str(office.id)


def _make_due(db_session, lead_id):
    """Lead'in bir sonraki takip vadesini geçmişe çeker (cron 'vadesi geldi' görsün)."""
    lead = db_session.get(Lead, lead_id)
    lead.next_follow_up_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()


# --- PATCH /leads/{id}/auto-follow-up ---


def test_toggle_requires_auth(client):
    resp = client.patch("/leads/does-not-exist/auto-follow-up", json={"enabled": True})
    assert resp.status_code == 401


def test_toggle_returns_503_without_whatsapp_number(client):
    headers = _register(client, "Ofis AutoFU 1", "owner1@autofu-test.com")
    lead_id = _create_lead(client, headers)

    resp = client.patch(f"/leads/{lead_id}/auto-follow-up", json={"enabled": True}, headers=headers)
    assert resp.status_code == 503


def test_toggle_on_schedules_first_stage(client, db_session):
    headers = _register(client, "Ofis AutoFU 2", "owner2@autofu-test.com")
    _set_phone_number_id(db_session, "Ofis AutoFU 2", "2000000001")
    lead_id = _create_lead(client, headers)

    resp = client.patch(f"/leads/{lead_id}/auto-follow-up", json={"enabled": True}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["auto_follow_up_enabled"] is True
    assert body["follow_up_stage"] == 0
    assert body["next_follow_up_at"] is not None

    resp = client.patch(f"/leads/{lead_id}/auto-follow-up", json={"enabled": False}, headers=headers)
    body = resp.json()
    assert body["auto_follow_up_enabled"] is False
    assert body["next_follow_up_at"] is None


# --- POST /internal/run-follow-ups (cron endpoint) ---


def test_run_follow_ups_returns_503_without_cron_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "cron_secret", None)
    resp = client.post("/internal/run-follow-ups")
    assert resp.status_code == 503


def test_run_follow_ups_rejects_wrong_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "cron_secret", "dogru-sir")
    resp = client.post("/internal/run-follow-ups", headers={"X-Cron-Secret": "yanlis-sir"})
    assert resp.status_code == 401
    resp = client.post("/internal/run-follow-ups")
    assert resp.status_code == 401


def test_run_follow_ups_reports_when_whatsapp_not_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "cron_secret", "test-sir")
    monkeypatch.setattr(settings, "whatsapp_token", None)
    resp = client.post("/internal/run-follow-ups", headers={"X-Cron-Secret": "test-sir"})
    assert resp.status_code == 200
    assert resp.json()["detail"] == "whatsapp_not_configured"


def test_run_follow_ups_sends_due_message_and_advances_stage(client, db_session, monkeypatch):
    headers = _register(client, "Ofis AutoFU 3", "owner3@autofu-test.com")
    _set_phone_number_id(db_session, "Ofis AutoFU 3", "2000000002")
    lead_id = _create_lead(client, headers, district="Moda", phone="905559998877")

    client.patch(f"/leads/{lead_id}/auto-follow-up", json={"enabled": True}, headers=headers)
    _make_due(db_session, lead_id)

    monkeypatch.setattr(settings, "cron_secret", "test-sir")
    monkeypatch.setattr(settings, "whatsapp_token", "test-token")
    sent_calls = []
    monkeypatch.setattr(
        follow_up,
        "send_whatsapp_text",
        lambda phone_number_id, to, text: sent_calls.append((phone_number_id, to, text)),
    )

    resp = client.post("/internal/run-follow-ups", headers={"X-Cron-Secret": "test-sir"})
    assert resp.status_code == 200
    assert resp.json()["sent"] == 1
    assert sent_calls[0][0] == "2000000002"
    assert sent_calls[0][1] == "905559998877"
    assert "Moda" in sent_calls[0][2]

    lead = client.get(f"/leads/{lead_id}", headers=headers).json()
    assert lead["follow_up_stage"] == 1
    assert lead["auto_follow_up_enabled"] is True
    assert lead["next_follow_up_at"] is not None
    assert lead["last_contacted_at"] is not None


def test_run_follow_ups_skips_leads_not_yet_due(client, db_session, monkeypatch):
    headers = _register(client, "Ofis AutoFU 4", "owner4@autofu-test.com")
    _set_phone_number_id(db_session, "Ofis AutoFU 4", "2000000003")
    lead_id = _create_lead(client, headers)

    # Zincir açık ama vade (1 gün sonra) henüz gelmedi — hiçbir şey gönderilmemeli.
    client.patch(f"/leads/{lead_id}/auto-follow-up", json={"enabled": True}, headers=headers)

    monkeypatch.setattr(settings, "cron_secret", "test-sir")
    monkeypatch.setattr(settings, "whatsapp_token", "test-token")
    sent_calls = []
    monkeypatch.setattr(
        follow_up, "send_whatsapp_text", lambda *args: sent_calls.append(args)
    )

    resp = client.post("/internal/run-follow-ups", headers={"X-Cron-Secret": "test-sir"})
    assert resp.status_code == 200
    assert resp.json()["sent"] == 0
    assert sent_calls == []


def test_chain_disables_itself_after_last_stage(client, db_session, monkeypatch):
    headers = _register(client, "Ofis AutoFU 5", "owner5@autofu-test.com")
    _set_phone_number_id(db_session, "Ofis AutoFU 5", "2000000004")
    lead_id = _create_lead(client, headers)
    client.patch(f"/leads/{lead_id}/auto-follow-up", json={"enabled": True}, headers=headers)

    monkeypatch.setattr(settings, "cron_secret", "test-sir")
    monkeypatch.setattr(settings, "whatsapp_token", "test-token")
    monkeypatch.setattr(follow_up, "send_whatsapp_text", lambda *args: None)

    for expected_stage in range(1, len(FOLLOW_UP_CHAIN) + 1):
        _make_due(db_session, lead_id)
        resp = client.post("/internal/run-follow-ups", headers={"X-Cron-Secret": "test-sir"})
        assert resp.json()["sent"] == 1
        lead = client.get(f"/leads/{lead_id}", headers=headers).json()
        assert lead["follow_up_stage"] == expected_stage

    # Son aşamadan sonra zincir kendini kapatır, tekrar mesaj gitmez.
    assert lead["auto_follow_up_enabled"] is False
    assert lead["next_follow_up_at"] is None
    resp = client.post("/internal/run-follow-ups", headers={"X-Cron-Secret": "test-sir"})
    assert resp.json()["sent"] == 0


def test_failed_send_does_not_advance_stage(client, db_session, monkeypatch):
    headers = _register(client, "Ofis AutoFU 6", "owner6@autofu-test.com")
    _set_phone_number_id(db_session, "Ofis AutoFU 6", "2000000005")
    lead_id = _create_lead(client, headers)
    client.patch(f"/leads/{lead_id}/auto-follow-up", json={"enabled": True}, headers=headers)
    _make_due(db_session, lead_id)

    monkeypatch.setattr(settings, "cron_secret", "test-sir")
    monkeypatch.setattr(settings, "whatsapp_token", "test-token")

    def _raise(*args):
        raise whatsapp_send.WhatsAppSendError("Meta hata döndürdü (durum kodu 500).")

    monkeypatch.setattr(follow_up, "send_whatsapp_text", _raise)

    resp = client.post("/internal/run-follow-ups", headers={"X-Cron-Secret": "test-sir"})
    assert resp.status_code == 200
    assert resp.json() == {"offices": 1, "sent": 0, "failed": 1}

    # Aşama ilerlemedi, vade hâlâ geçmişte → bir sonraki cron'da yeniden denenir.
    lead = client.get(f"/leads/{lead_id}", headers=headers).json()
    assert lead["follow_up_stage"] == 0
    assert lead["auto_follow_up_enabled"] is True


def test_inbound_reply_stops_the_chain(client, db_session):
    headers = _register(client, "Ofis AutoFU 7", "owner7@autofu-test.com")
    office_id = _set_phone_number_id(db_session, "Ofis AutoFU 7", "2000000006")
    lead_id = _create_lead(client, headers, phone="905550001122")
    client.patch(f"/leads/{lead_id}/auto-follow-up", json={"enabled": True}, headers=headers)

    # Aday WhatsApp'tan yanıt verdi (Intake Agent akışı) → zincir durmalı.
    process_inbound_message(
        db_session,
        office_id=office_id,
        external_message_id="wamid.autofu-reply-1",
        contact_phone="905550001122",
    )

    lead = client.get(f"/leads/{lead_id}", headers=headers).json()
    assert lead["auto_follow_up_enabled"] is False
    assert lead["next_follow_up_at"] is None
    assert lead["message_count"] == 1
