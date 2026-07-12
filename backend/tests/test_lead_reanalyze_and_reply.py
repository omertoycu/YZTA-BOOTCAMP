from datetime import datetime, timezone

from sqlalchemy import select

from app.agents import reply_draft
from app.agents import whatsapp_extract
from app.api.routes import leads as leads_route
from app.models.lead import Lead
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


def _add_inbound_message(db_session, lead_id, office_id, body):
    db_session.add(
        WhatsAppMessage(
            office_id=office_id, lead_id=lead_id, direction="in", message_type="text", body=body
        )
    )
    db_session.commit()


def test_reanalyze_requires_existing_inbound_text_messages(client):
    headers = _register(client, "Ofis Reanalyze Test 1", "owner1@reanalyze-test.com")
    lead_id = _create_lead(client, headers)

    resp = client.post(f"/leads/{lead_id}/reanalyze-messages", headers=headers)
    assert resp.status_code == 422


def test_reanalyze_returns_draft_without_writing_lead_fields(client, db_session, monkeypatch):
    headers = _register(client, "Ofis Reanalyze Test 2", "owner2@reanalyze-test.com")
    lead_id = _create_lead(client, headers)
    lead = db_session.execute(select(Lead).where(Lead.id == lead_id)).scalar_one()
    _add_inbound_message(db_session, lead_id, lead.office_id, "Kadıköy'de 3+1 arıyorum")

    def _fake_extract(text):
        return {
            "district": "Kadıköy", "budget_min": None, "budget_max": 5_000_000,
            "room_count": "3+1", "radius_km": None,
        }

    monkeypatch.setattr(leads_route, "extract_lead_fields", _fake_extract)

    resp = client.post(f"/leads/{lead_id}/reanalyze-messages", headers=headers)
    assert resp.status_code == 200
    draft = resp.json()
    assert draft["district"] == "Kadıköy"
    assert draft["budget_max"] == 5_000_000

    # Lead'in kendisi HİÇBİR ŞEKİLDE değişmemeli — sadece taslak döner.
    fresh = client.get(f"/leads/{lead_id}", headers=headers).json()
    assert fresh["district"] is None
    assert fresh["budget_max"] is None
    assert fresh["fields_extracted_by_ai"] is False


def test_reanalyze_uses_sliding_window_of_recent_messages(client, db_session, monkeypatch):
    """Token maliyeti sınırsız büyümesin: Gemini'ye tüm geçmiş değil sadece son
    REANALYZE_MESSAGE_WINDOW mesaj, kronolojik sırada gönderilir."""
    headers = _register(client, "Ofis Reanalyze Pencere", "owner-pencere@reanalyze-test.com")
    lead_id = _create_lead(client, headers)
    lead = db_session.execute(select(Lead).where(Lead.id == lead_id)).scalar_one()
    for i in range(1, 7):
        _add_inbound_message(db_session, lead_id, lead.office_id, f"mesaj {i}")

    captured = []

    def _capture_extract(text):
        captured.append(text)
        return {field: None for field in whatsapp_extract.EXTRACTABLE_LEAD_FIELDS}

    monkeypatch.setattr(leads_route, "extract_lead_fields", _capture_extract)

    resp = client.post(f"/leads/{lead_id}/reanalyze-messages", headers=headers)
    assert resp.status_code == 200
    assert captured[0] == "mesaj 3\nmesaj 4\nmesaj 5\nmesaj 6"


def test_reanalyze_respects_rate_cap(client, db_session, monkeypatch):
    headers = _register(client, "Ofis Reanalyze Test 3", "owner3@reanalyze-test.com")
    lead_id = _create_lead(client, headers)
    lead = db_session.execute(select(Lead).where(Lead.id == lead_id)).scalar_one()
    _add_inbound_message(db_session, lead_id, lead.office_id, "Kadıköy'de 3+1 arıyorum")

    lead.llm_extraction_count = whatsapp_extract.MAX_EXTRACTIONS_PER_24H
    lead.last_llm_extraction_at = datetime.now(timezone.utc)
    db_session.commit()

    resp = client.post(f"/leads/{lead_id}/reanalyze-messages", headers=headers)
    assert resp.status_code == 429


def test_reanalyze_returns_503_when_not_configured(client, db_session, monkeypatch):
    headers = _register(client, "Ofis Reanalyze Test 4", "owner4@reanalyze-test.com")
    lead_id = _create_lead(client, headers)
    lead = db_session.execute(select(Lead).where(Lead.id == lead_id)).scalar_one()
    _add_inbound_message(db_session, lead_id, lead.office_id, "Kadıköy'de 3+1 arıyorum")

    def _raise(text):
        raise whatsapp_extract.WhatsAppExtractError("__not_configured__")

    monkeypatch.setattr(leads_route, "extract_lead_fields", _raise)

    resp = client.post(f"/leads/{lead_id}/reanalyze-messages", headers=headers)
    assert resp.status_code == 503


def test_suggest_reply_appends_public_links_after_llm_draft(client, db_session, monkeypatch):
    """İlan linkleri LLM prompt'una girmez (URL bozma riski) — taslağın sonuna
    deterministik eklenir; danışman özet cümlesini de (yapısal alanlardan,
    Gemini'siz) prompt bağlamı olarak alır."""
    headers = _register(client, "Ofis Reanalyze Link", "owner-link@reanalyze-test.com")
    listing = client.post(
        "/listings",
        json={"title": "Kadıköy 3+1 Işıklı Daire", "district": "Kadıköy", "price": 5_000_000, "room_count": "3+1"},
        headers=headers,
    ).json()
    lead_id = _create_lead(client, headers, district="Kadıköy", room_count="3+1", budget_max=6_000_000)

    captured_kwargs = {}

    def _fake_draft_reply(**kwargs):
        captured_kwargs.update(kwargs)
        return "Size uygun bir portföyümüz var."

    monkeypatch.setattr(leads_route, "draft_reply", _fake_draft_reply)

    resp = client.post(f"/leads/{lead_id}/suggest-reply", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["match_count"] == 1
    assert body["draft"].startswith("Size uygun bir portföyümüz var.")
    assert f"/p/{listing['id']}" in body["draft"]
    # Hibrit özet: yapısal alanlar dolu → deterministik cümle prompt'a gitmiş olmalı.
    assert captured_kwargs["lead_summary"] is not None
    assert "Kadıköy" in captured_kwargs["lead_summary"]


def test_suggest_reply_returns_draft_with_match_count(client, db_session, monkeypatch):
    headers = _register(client, "Ofis Reanalyze Test 5", "owner5@reanalyze-test.com")
    lead_id = _create_lead(client, headers, district="Kadıköy", room_count="3+1", budget_max=6_000_000)
    lead = db_session.execute(select(Lead).where(Lead.id == lead_id)).scalar_one()
    _add_inbound_message(db_session, lead_id, lead.office_id, "Kadıköy'de 3+1 arıyorum")

    def _fake_draft_reply(**kwargs):
        assert kwargs["district"] == "Kadıköy"
        return "Merhaba, size uygun bir portföyümüz var."

    monkeypatch.setattr(leads_route, "draft_reply", _fake_draft_reply)

    resp = client.post(f"/leads/{lead_id}/suggest-reply", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["draft"] == "Merhaba, size uygun bir portföyümüz var."
    assert body["match_count"] == 0  # portföy eklenmedi, eşleşme yok ama draft yine dönmeli


def test_suggest_reply_returns_503_when_not_configured(client, db_session, monkeypatch):
    headers = _register(client, "Ofis Reanalyze Test 6", "owner6@reanalyze-test.com")
    lead_id = _create_lead(client, headers)

    def _raise(**kwargs):
        raise reply_draft.ReplyDraftError("__not_configured__")

    monkeypatch.setattr(leads_route, "draft_reply", _raise)

    resp = client.post(f"/leads/{lead_id}/suggest-reply", headers=headers)
    assert resp.status_code == 503
