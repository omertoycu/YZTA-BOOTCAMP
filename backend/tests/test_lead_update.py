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


def test_patch_lead_updates_only_provided_fields(client):
    headers = _register(client, "Ofis Lead Update Test 1", "owner1@lead-update-test.com")
    lead_id = _create_lead(client, headers, district="Beşiktaş", budget_max=3_000_000)

    resp = client.patch(f"/leads/{lead_id}", json={"district": "Kadıköy"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["district"] == "Kadıköy"
    assert body["budget_max"] == 3_000_000  # gönderilmeyen alan değişmedi


def test_patch_lead_clears_ai_flag(client, db_session):
    from sqlalchemy import select

    from app.models.lead import Lead

    headers = _register(client, "Ofis Lead Update Test 2", "owner2@lead-update-test.com")
    lead_id = _create_lead(client, headers)

    lead = db_session.execute(select(Lead).where(Lead.id == lead_id)).scalar_one()
    lead.fields_extracted_by_ai = True
    db_session.commit()

    resp = client.patch(f"/leads/{lead_id}", json={"room_count": "2+1"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["fields_extracted_by_ai"] is False


def test_patch_lead_empty_body_keeps_ai_flag(client, db_session):
    from sqlalchemy import select

    from app.models.lead import Lead

    headers = _register(client, "Ofis Lead Update Test 3", "owner3@lead-update-test.com")
    lead_id = _create_lead(client, headers)

    lead = db_session.execute(select(Lead).where(Lead.id == lead_id)).scalar_one()
    lead.fields_extracted_by_ai = True
    db_session.commit()

    resp = client.patch(f"/leads/{lead_id}", json={}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["fields_extracted_by_ai"] is True


def test_patch_lead_unknown_lead_404(client):
    headers = _register(client, "Ofis Lead Update Test 4", "owner4@lead-update-test.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.patch(f"/leads/{fake_id}", json={"district": "Kadıköy"}, headers=headers)
    assert resp.status_code == 404


def test_patch_lead_requires_auth(client):
    resp = client.patch(
        "/leads/00000000-0000-0000-0000-000000000000", json={"district": "Kadıköy"}
    )
    assert resp.status_code == 401
