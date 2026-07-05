import io

from app.agents import lead_voice_note
from app.api.routes import leads as leads_route


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


def test_voice_note_requires_auth(client):
    resp = client.post(
        "/leads/00000000-0000-0000-0000-000000000000/voice-note",
        files={"file": ("note.webm", io.BytesIO(b"fake-audio"), "audio/webm")},
    )
    assert resp.status_code == 401


def test_voice_note_unknown_lead_returns_404(client):
    headers = _register(client, "Ofis Voice Note Test 1", "owner1@voice-note-test.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.post(
        f"/leads/{fake_id}/voice-note",
        files={"file": ("note.webm", io.BytesIO(b"fake-audio"), "audio/webm")},
        headers=headers,
    )
    assert resp.status_code == 404


def test_voice_note_returns_structured_draft(client, monkeypatch):
    headers = _register(client, "Ofis Voice Note Test 2", "owner2@voice-note-test.com")
    lead_id = _create_lead(client, headers)

    def _fake_transcribe(audio_bytes, content_type):
        return {
            "transcript": "Ahmet bey daireyi beğendi ama fiyatı yüksek buldu, cuma günü tekrar arayacağım",
            "note_summary": "Fiyatı yüksek buldu, cuma tekrar aranacak.",
            "suggested_status": "negotiation",
            "reminder_at": None,
            "reminder_note": "Fiyat konusunda tekrar ara",
        }

    monkeypatch.setattr(leads_route, "transcribe_and_extract_note", _fake_transcribe)

    resp = client.post(
        f"/leads/{lead_id}/voice-note",
        files={"file": ("note.webm", io.BytesIO(b"fake-audio"), "audio/webm")},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["suggested_status"] == "negotiation"
    assert body["reminder_note"] == "Fiyat konusunda tekrar ara"


def test_voice_note_returns_503_when_not_configured(client, monkeypatch):
    headers = _register(client, "Ofis Voice Note Test 3", "owner3@voice-note-test.com")
    lead_id = _create_lead(client, headers)

    def _raise(audio_bytes, content_type):
        raise lead_voice_note.VoiceNoteError("__not_configured__")

    monkeypatch.setattr(leads_route, "transcribe_and_extract_note", _raise)

    resp = client.post(
        f"/leads/{lead_id}/voice-note",
        files={"file": ("note.webm", io.BytesIO(b"fake-audio"), "audio/webm")},
        headers=headers,
    )
    assert resp.status_code == 503


def test_voice_note_returns_502_on_model_error(client, monkeypatch):
    headers = _register(client, "Ofis Voice Note Test 4", "owner4@voice-note-test.com")
    lead_id = _create_lead(client, headers)

    def _raise(audio_bytes, content_type):
        raise lead_voice_note.VoiceNoteError("Model yanıtı ayrıştırılamadı, tekrar deneyin.")

    monkeypatch.setattr(leads_route, "transcribe_and_extract_note", _raise)

    resp = client.post(
        f"/leads/{lead_id}/voice-note",
        files={"file": ("note.webm", io.BytesIO(b"fake-audio"), "audio/webm")},
        headers=headers,
    )
    assert resp.status_code == 502


def test_voice_note_rejects_empty_file(client):
    headers = _register(client, "Ofis Voice Note Test 5", "owner5@voice-note-test.com")
    lead_id = _create_lead(client, headers)
    resp = client.post(
        f"/leads/{lead_id}/voice-note",
        files={"file": ("note.webm", io.BytesIO(b""), "audio/webm")},
        headers=headers,
    )
    assert resp.status_code == 422


def test_suggested_status_outside_allowed_set_is_dropped(monkeypatch):
    def _fake_generate_content(self, parts, generation_config=None):
        class _Resp:
            text = (
                '{"transcript": "test", "note_summary": "ozet", '
                '"suggested_status": "not_a_real_status", "reminder_date": null, "reminder_note": null}'
            )

        return _Resp()

    monkeypatch.setattr(lead_voice_note.settings, "gemini_api_key", "fake-key")
    monkeypatch.setattr("google.generativeai.configure", lambda **kwargs: None)
    monkeypatch.setattr("google.generativeai.GenerativeModel.generate_content", _fake_generate_content)

    result = lead_voice_note.transcribe_and_extract_note(b"fake-audio", "audio/webm")
    assert result["suggested_status"] is None


def test_reminder_endpoint_sets_and_clears(client):
    headers = _register(client, "Ofis Voice Note Test 6", "owner6@voice-note-test.com")
    lead_id = _create_lead(client, headers)

    resp = client.patch(
        f"/leads/{lead_id}/reminder",
        json={"reminder_at": "2026-07-11T09:00:00Z", "reminder_note": "Fiyat konusunda tekrar ara"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reminder_note"] == "Fiyat konusunda tekrar ara"
    assert body["reminder_at"] is not None

    resp = client.patch(
        f"/leads/{lead_id}/reminder",
        json={"reminder_at": None, "reminder_note": None},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reminder_at"] is None
    assert body["reminder_note"] is None
