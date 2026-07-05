from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.agents import appointment_reminder
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


def _create_lead(client, headers, phone="905551112233"):
    resp = client.post("/leads", json={"contact_phone": phone}, headers=headers)
    return resp.json()["id"]


def _set_phone_number_id(db_session, office_name, phone_number_id):
    office = db_session.execute(select(Office).where(Office.name == office_name)).scalar_one()
    office.whatsapp_phone_number_id = phone_number_id
    db_session.commit()


# --- POST /leads/{id}/appointment ---


def test_create_appointment_without_whatsapp_still_saves(client):
    headers = _register(client, "Ofis Appt Test 1", "owner@appt-test-1.com")
    lead_id = _create_lead(client, headers)

    resp = client.post(
        f"/leads/{lead_id}/appointment",
        json={
            "appointment_at": "2026-07-10T14:00:00Z",
            "location": "Kadıköy, İstanbul",
            "send_whatsapp_confirmation": False,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["whatsapp_confirmation_sent"] is False
    assert body["whatsapp_confirmation_error"] is None
    assert body["lead"]["appointment_location"] == "Kadıköy, İstanbul"
    assert body["lead"]["appointment_at"] is not None


def test_create_appointment_reports_whatsapp_not_connected(client):
    headers = _register(client, "Ofis Appt Test 2", "owner@appt-test-2.com")
    lead_id = _create_lead(client, headers)

    resp = client.post(
        f"/leads/{lead_id}/appointment",
        json={
            "appointment_at": "2026-07-10T14:00:00Z",
            "location": "Beşiktaş",
            "send_whatsapp_confirmation": True,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["whatsapp_confirmation_sent"] is False
    assert body["whatsapp_confirmation_error"] == "Bu ofis için WhatsApp gönderimi henüz bağlı değil"
    # Randevu WhatsApp başarısız olsa da kaydedilmiş olmalı.
    assert body["lead"]["appointment_location"] == "Beşiktaş"


def test_create_appointment_sends_whatsapp_confirmation(client, db_session, monkeypatch):
    headers = _register(client, "Ofis Appt Test 3", "owner@appt-test-3.com")
    _set_phone_number_id(db_session, "Ofis Appt Test 3", "3000000001")
    lead_id = _create_lead(client, headers, phone="905559990001")

    monkeypatch.setattr(settings, "whatsapp_token", "test-token")
    sent_calls = []
    monkeypatch.setattr(
        "app.api.routes.leads.send_whatsapp_text",
        lambda phone_number_id, to, text: sent_calls.append((phone_number_id, to, text)),
    )

    resp = client.post(
        f"/leads/{lead_id}/appointment",
        json={"appointment_at": "2026-07-10T14:00:00Z", "location": "Beşiktaş"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["whatsapp_confirmation_sent"] is True
    assert sent_calls[0][0] == "3000000001"
    assert sent_calls[0][1] == "905559990001"
    assert "Beşiktaş" in sent_calls[0][2]


def test_create_appointment_unknown_lead_returns_404(client):
    headers = _register(client, "Ofis Appt Test 4", "owner@appt-test-4.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.post(
        f"/leads/{fake_id}/appointment",
        json={"appointment_at": "2026-07-10T14:00:00Z", "location": "Beşiktaş", "send_whatsapp_confirmation": False},
        headers=headers,
    )
    assert resp.status_code == 404


# --- DELETE /leads/{id}/appointment ---


def test_cancel_appointment_clears_fields(client):
    headers = _register(client, "Ofis Appt Test 5", "owner@appt-test-5.com")
    lead_id = _create_lead(client, headers)
    client.post(
        f"/leads/{lead_id}/appointment",
        json={"appointment_at": "2026-07-10T14:00:00Z", "location": "Beşiktaş", "send_whatsapp_confirmation": False},
        headers=headers,
    )

    resp = client.delete(f"/leads/{lead_id}/appointment", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["appointment_at"] is None
    assert body["appointment_location"] is None


# --- GET /leads/{id}/appointment.ics ---


def test_appointment_ics_returns_calendar_file(client):
    headers = _register(client, "Ofis Appt Test 6", "owner@appt-test-6.com")
    lead_id = _create_lead(client, headers)
    client.post(
        f"/leads/{lead_id}/appointment",
        json={"appointment_at": "2026-07-10T14:00:00Z", "location": "Beşiktaş", "send_whatsapp_confirmation": False},
        headers=headers,
    )

    resp = client.get(f"/leads/{lead_id}/appointment.ics", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/calendar")
    assert b"BEGIN:VCALENDAR" in resp.content
    assert b"LOCATION:Be\xc5\x9fikta\xc5\x9f" in resp.content


def test_appointment_ics_404_when_no_appointment_set(client):
    headers = _register(client, "Ofis Appt Test 7", "owner@appt-test-7.com")
    lead_id = _create_lead(client, headers)

    resp = client.get(f"/leads/{lead_id}/appointment.ics", headers=headers)
    assert resp.status_code == 404


# --- POST /internal/run-appointment-reminders ---


def test_run_appointment_reminders_requires_cron_secret(client, monkeypatch):
    resp = client.post("/internal/run-appointment-reminders")
    assert resp.status_code == 503

    monkeypatch.setattr(settings, "cron_secret", "test-sir")
    resp = client.post("/internal/run-appointment-reminders", headers={"X-Cron-Secret": "yanlis"})
    assert resp.status_code == 401


def test_run_appointment_reminders_sends_for_due_appointment(client, db_session, monkeypatch):
    headers = _register(client, "Ofis Appt Test 8", "owner@appt-test-8.com")
    _set_phone_number_id(db_session, "Ofis Appt Test 8", "3000000002")
    lead_id = _create_lead(client, headers, phone="905559990002")

    soon = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()
    client.post(
        f"/leads/{lead_id}/appointment",
        json={"appointment_at": soon, "location": "Şişli", "send_whatsapp_confirmation": False},
        headers=headers,
    )

    monkeypatch.setattr(settings, "cron_secret", "test-sir")
    monkeypatch.setattr(settings, "whatsapp_token", "test-token")
    sent_calls = []
    monkeypatch.setattr(
        appointment_reminder,
        "send_whatsapp_text",
        lambda phone_number_id, to, text: sent_calls.append((phone_number_id, to, text)),
    )

    resp = client.post("/internal/run-appointment-reminders", headers={"X-Cron-Secret": "test-sir"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["sent"] == 1
    assert sent_calls[0][0] == "3000000002"
    assert "Şişli" in sent_calls[0][2]

    lead = db_session.get(Lead, lead_id)
    assert lead.appointment_reminder_sent is True

    # İkinci çalıştırmada tekrar gönderilmemeli.
    resp2 = client.post("/internal/run-appointment-reminders", headers={"X-Cron-Secret": "test-sir"})
    assert resp2.json()["sent"] == 0


def test_run_appointment_reminders_skips_appointment_too_far_away(client, db_session, monkeypatch):
    headers = _register(client, "Ofis Appt Test 9", "owner@appt-test-9.com")
    _set_phone_number_id(db_session, "Ofis Appt Test 9", "3000000003")
    lead_id = _create_lead(client, headers, phone="905559990003")

    far_future = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    client.post(
        f"/leads/{lead_id}/appointment",
        json={"appointment_at": far_future, "location": "Ümraniye", "send_whatsapp_confirmation": False},
        headers=headers,
    )

    monkeypatch.setattr(settings, "cron_secret", "test-sir")
    monkeypatch.setattr(settings, "whatsapp_token", "test-token")
    sent_calls = []
    monkeypatch.setattr(
        appointment_reminder, "send_whatsapp_text", lambda *args: sent_calls.append(args)
    )

    resp = client.post("/internal/run-appointment-reminders", headers={"X-Cron-Secret": "test-sir"})
    assert resp.status_code == 200
    assert resp.json()["sent"] == 0
    assert sent_calls == []


def test_run_appointment_reminders_reports_when_whatsapp_not_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "cron_secret", "test-sir")
    monkeypatch.setattr(settings, "whatsapp_token", None)
    resp = client.post("/internal/run-appointment-reminders", headers={"X-Cron-Secret": "test-sir"})
    assert resp.status_code == 200
    assert resp.json()["detail"] == "whatsapp_not_configured"
