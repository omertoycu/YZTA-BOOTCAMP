from datetime import datetime, timezone

from app.models.lead import Lead
from app.models.whatsapp_message import WhatsAppMessage
from sqlalchemy import select


def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "supersecret123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_lead(client, headers, **overrides):
    payload = {"contact_phone": "5551234567"}
    payload.update(overrides)
    resp = client.post("/leads", json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def test_list_lead_messages_returns_401_without_auth(client):
    resp = client.get("/leads/00000000-0000-0000-0000-000000000000/messages")
    assert resp.status_code == 401


def test_list_lead_messages_chronological_order(client, db_session):
    headers = _register(client, "Ofis Lead Messages Test 1", "owner1@lead-messages-test.com")
    lead_id = _create_lead(client, headers)

    lead = db_session.execute(select(Lead).where(Lead.id == lead_id)).scalar_one()
    base = datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc)
    db_session.add(
        WhatsAppMessage(
            office_id=lead.office_id, lead_id=lead.id, direction="in",
            message_type="text", body="ikinci", created_at=base.replace(hour=11),
        )
    )
    db_session.add(
        WhatsAppMessage(
            office_id=lead.office_id, lead_id=lead.id, direction="out",
            message_type="text", body="birinci", created_at=base,
        )
    )
    db_session.commit()

    resp = client.get(f"/leads/{lead_id}/messages", headers=headers)
    assert resp.status_code == 200
    bodies = [m["body"] for m in resp.json()]
    assert bodies == ["birinci", "ikinci"]


def test_list_lead_messages_unknown_lead_404(client):
    headers = _register(client, "Ofis Lead Messages Test 2", "owner2@lead-messages-test.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/leads/{fake_id}/messages", headers=headers)
    assert resp.status_code == 404
