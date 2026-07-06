from sqlalchemy import select

from app.models.lead_note import LeadNote
from app.models.lead_score import LeadScore
from app.models.whatsapp_message import WhatsAppMessage


def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "Supersecret123!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_lead(client, headers, **overrides):
    payload = {"contact_phone": "5551234567"}
    payload.update(overrides)
    resp = client.post("/leads", json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def test_delete_lead_requires_auth(client):
    resp = client.delete("/leads/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 401


def test_delete_unknown_lead_returns_404(client):
    headers = _register(client, "Ofis Lead Delete Test 1", "owner1@lead-delete-test.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.delete(f"/leads/{fake_id}", headers=headers)
    assert resp.status_code == 404


def test_delete_lead_removes_it_and_returns_404_after(client):
    headers = _register(client, "Ofis Lead Delete Test 2", "owner2@lead-delete-test.com")
    lead_id = _create_lead(client, headers)

    resp = client.delete(f"/leads/{lead_id}", headers=headers)
    assert resp.status_code == 204

    resp = client.get(f"/leads/{lead_id}", headers=headers)
    assert resp.status_code == 404


def test_delete_lead_cascades_notes_scores_and_messages(client, db_session):
    headers = _register(client, "Ofis Lead Delete Test 3", "owner3@lead-delete-test.com")
    lead_id = _create_lead(client, headers)

    # Notlar (gerçek endpoint üzerinden), skor, ve bir whatsapp mesajı ekle —
    # cascade olmasaydı bunlardan biri bile silmeyi ForeignKeyViolation ile
    # engellerdi.
    note_resp = client.post(f"/leads/{lead_id}/notes", json={"body": "test notu"}, headers=headers)
    assert note_resp.status_code == 201
    score_resp = client.post(f"/leads/{lead_id}/score", headers=headers)
    assert score_resp.status_code == 201

    lead_rows = db_session.execute(
        select(LeadNote).where(LeadNote.lead_id == lead_id)
    ).scalars().all()
    assert len(lead_rows) == 1
    office_id = lead_rows[0].office_id
    db_session.add(
        WhatsAppMessage(office_id=office_id, lead_id=lead_id, direction="in", message_type="text", body="merhaba")
    )
    db_session.commit()

    resp = client.delete(f"/leads/{lead_id}", headers=headers)
    assert resp.status_code == 204

    assert db_session.execute(select(LeadNote).where(LeadNote.lead_id == lead_id)).scalars().all() == []
    assert db_session.execute(select(LeadScore).where(LeadScore.lead_id == lead_id)).scalars().all() == []
    assert (
        db_session.execute(select(WhatsAppMessage).where(WhatsAppMessage.lead_id == lead_id)).scalars().all() == []
    )
