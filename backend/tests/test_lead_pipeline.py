from sqlalchemy import select

from app.api.routes import leads as leads_route
from app.models.office import Office


def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "Supersecret123!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_lead(client, headers, **overrides):
    payload = {"contact_phone": "905551112233", "district": "Kadıköy", **overrides}
    resp = client.post("/leads", json=payload, headers=headers)
    return resp.json()["id"]


def _set_phone_number_id(db_session, office_name, phone_number_id):
    office = db_session.execute(select(Office).where(Office.name == office_name)).scalar_one()
    office.whatsapp_phone_number_id = phone_number_id
    db_session.commit()


# --- PATCH /leads/{id}/status ---


def test_new_lead_starts_in_new_status(client):
    headers = _register(client, "Ofis Pipeline 1", "owner1@pipeline-test.com")
    lead_id = _create_lead(client, headers)
    lead = client.get(f"/leads/{lead_id}", headers=headers).json()
    assert lead["status"] == "new"


def test_status_update_moves_lead_through_funnel(client):
    headers = _register(client, "Ofis Pipeline 2", "owner2@pipeline-test.com")
    lead_id = _create_lead(client, headers)

    resp = client.patch(f"/leads/{lead_id}/status", json={"status": "viewing"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "viewing"


def test_status_update_rejects_invalid_status(client):
    headers = _register(client, "Ofis Pipeline 3", "owner3@pipeline-test.com")
    lead_id = _create_lead(client, headers)
    resp = client.patch(f"/leads/{lead_id}/status", json={"status": "uzayda"}, headers=headers)
    assert resp.status_code == 400


def test_won_status_stops_auto_follow_up(client, db_session):
    headers = _register(client, "Ofis Pipeline 4", "owner4@pipeline-test.com")
    _set_phone_number_id(db_session, "Ofis Pipeline 4", "3000000001")
    lead_id = _create_lead(client, headers)
    client.patch(f"/leads/{lead_id}/auto-follow-up", json={"enabled": True}, headers=headers)

    resp = client.patch(f"/leads/{lead_id}/status", json={"status": "won"}, headers=headers)
    body = resp.json()
    assert body["status"] == "won"
    # Kapanmış bir konuşmaya otomatik takip mesajı gitmemeli.
    assert body["auto_follow_up_enabled"] is False
    assert body["next_follow_up_at"] is None


# --- Lead notları ---


def test_note_create_and_list(client):
    headers = _register(client, "Ofis Pipeline 5", "owner5@pipeline-test.com")
    lead_id = _create_lead(client, headers)

    resp = client.post(
        f"/leads/{lead_id}/notes", json={"body": "Yarın 14:00 yer gösterimi."}, headers=headers
    )
    assert resp.status_code == 201
    note = resp.json()
    assert note["body"] == "Yarın 14:00 yer gösterimi."
    assert note["author_email"] == "owner5@pipeline-test.com"

    client.post(f"/leads/{lead_id}/notes", json={"body": "Bütçesi esnek."}, headers=headers)
    notes = client.get(f"/leads/{lead_id}/notes", headers=headers).json()
    assert len(notes) == 2
    # En yeni not en üstte.
    assert notes[0]["body"] == "Bütçesi esnek."


def test_note_rejects_blank_body(client):
    headers = _register(client, "Ofis Pipeline 6", "owner6@pipeline-test.com")
    lead_id = _create_lead(client, headers)
    resp = client.post(f"/leads/{lead_id}/notes", json={"body": "   "}, headers=headers)
    assert resp.status_code == 422


def test_notes_are_tenant_isolated(client):
    headers_a = _register(client, "Ofis Pipeline 7A", "owner7a@pipeline-test.com")
    headers_b = _register(client, "Ofis Pipeline 7B", "owner7b@pipeline-test.com")
    lead_id = _create_lead(client, headers_a)
    client.post(f"/leads/{lead_id}/notes", json={"body": "Gizli ofis notu"}, headers=headers_a)

    # B ofisi A'nın lead'ini göremez — RLS satırı gizler, 404 döner.
    resp = client.get(f"/leads/{lead_id}/notes", headers=headers_b)
    assert resp.status_code == 404


# --- POST /leads/{id}/send-matches ---


def test_send_matches_returns_503_without_whatsapp_number(client):
    headers = _register(client, "Ofis Pipeline 8", "owner8@pipeline-test.com")
    lead_id = _create_lead(client, headers)
    resp = client.post(f"/leads/{lead_id}/send-matches", headers=headers)
    assert resp.status_code == 503


def test_send_matches_sends_top_matches(client, db_session, monkeypatch):
    headers = _register(client, "Ofis Pipeline 9", "owner9@pipeline-test.com")
    _set_phone_number_id(db_session, "Ofis Pipeline 9", "3000000002")

    client.post(
        "/listings",
        json={"title": "Kadıköy'de 2+1", "district": "Kadıköy", "price": 2000000, "room_count": "2+1"},
        headers=headers,
    )
    lead_id = _create_lead(client, headers, budget_max=3000000, room_count="2+1")

    sent_calls = []
    monkeypatch.setattr(
        leads_route,
        "send_whatsapp_text",
        lambda phone_number_id, to, text: sent_calls.append((phone_number_id, to, text)),
    )

    resp = client.post(f"/leads/{lead_id}/send-matches", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["sent"] is True
    assert body["match_count"] == 1
    assert "Kadıköy'de 2+1" in sent_calls[0][2]
    assert "2.000.000" in sent_calls[0][2]

    # Gönderim son temas zamanını günceller.
    lead = client.get(f"/leads/{lead_id}", headers=headers).json()
    assert lead["last_contacted_at"] is not None


def test_send_matches_404_when_no_match(client, db_session, monkeypatch):
    headers = _register(client, "Ofis Pipeline 10", "owner10@pipeline-test.com")
    _set_phone_number_id(db_session, "Ofis Pipeline 10", "3000000003")
    lead_id = _create_lead(client, headers, district="Olmayan Bölge")

    monkeypatch.setattr(leads_route, "send_whatsapp_text", lambda *args: None)
    resp = client.post(f"/leads/{lead_id}/send-matches", headers=headers)
    assert resp.status_code == 404


# --- İlan durumu ---


def test_listing_status_update_and_matching_exclusion(client):
    headers = _register(client, "Ofis Pipeline 11", "owner11@pipeline-test.com")
    listing = client.post(
        "/listings",
        json={"title": "Satılacak daire", "district": "Moda", "price": 1500000, "room_count": "1+1"},
        headers=headers,
    ).json()

    resp = client.patch(f"/listings/{listing['id']}/status", json={"status": "sold"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "sold"

    resp = client.patch(f"/listings/{listing['id']}/status", json={"status": "kayip"}, headers=headers)
    assert resp.status_code == 400

    # Satılan portföy eşleştirmeye girmez.
    lead_id = _create_lead(client, headers, district="Moda", room_count="1+1", budget_max=2000000)
    matches = client.post(f"/leads/{lead_id}/match", headers=headers).json()
    assert matches == []


# --- Reports genişletmesi ---


def test_reports_include_pipeline_metrics(client, db_session):
    headers = _register(client, "Ofis Pipeline 12", "owner12@pipeline-test.com")
    _set_phone_number_id(db_session, "Ofis Pipeline 12", "3000000004")

    won_lead = _create_lead(client, headers)
    client.patch(f"/leads/{won_lead}/status", json={"status": "won"}, headers=headers)
    followed_lead = _create_lead(client, headers, contact_phone="905550009988")
    client.patch(f"/leads/{followed_lead}/auto-follow-up", json={"enabled": True}, headers=headers)

    overview = client.get("/reports/overview", headers=headers).json()
    assert overview["leads_by_status"]["won"] == 1
    assert overview["leads_by_status"]["new"] == 1
    assert overview["won_lead_count"] == 1
    assert overview["active_follow_up_count"] == 1
