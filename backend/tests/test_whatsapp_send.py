from sqlalchemy import select

from app.agents import whatsapp_send
from app.api.routes import leads as leads_route
from app.models.office import Office


def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "supersecret123"},
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


def test_follow_up_returns_502_on_send_failure(client, db_session, monkeypatch):
    headers = _register(client, "Ofis FollowUp Test 3", "owner3@followup-test.com")
    _set_phone_number_id(db_session, "Ofis FollowUp Test 3", "1000000011")
    lead_id = _create_lead(client, headers)

    def _raise(phone_number_id, to, text):
        raise whatsapp_send.WhatsAppSendError("Meta hata döndürdü (durum kodu 500).")

    monkeypatch.setattr(leads_route, "send_whatsapp_text", _raise)

    resp = client.post(f"/leads/{lead_id}/follow-up", json={}, headers=headers)
    assert resp.status_code == 502
