import io

from app.agents import voice_listing
from app.api.routes import listings as listings_route


def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "Supersecret123!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_voice_draft_requires_auth(client):
    resp = client.post(
        "/listings/voice-draft",
        files={"file": ("note.webm", io.BytesIO(b"fake-audio"), "audio/webm")},
    )
    assert resp.status_code == 401


def test_voice_draft_returns_structured_fields(client, monkeypatch):
    headers = _register(client, "Ofis Voice Test 1", "owner1@voice-test.com")

    def _fake_transcribe(audio_bytes, content_type):
        return {
            "transcript": "3 artı 1, Kadıköy'de, 8 milyon TL, satılık",
            "title": "Kadıköy'de ferah 3+1",
            "district": "Kadıköy",
            "price": 8_000_000.0,
            "room_count": "3+1",
            "square_meters": None,
            "listing_type": "sale",
        }

    monkeypatch.setattr(listings_route, "transcribe_and_extract", _fake_transcribe)

    resp = client.post(
        "/listings/voice-draft",
        files={"file": ("note.webm", io.BytesIO(b"fake-audio"), "audio/webm")},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["transcript"].startswith("3 artı 1")
    assert body["district"] == "Kadıköy"
    assert body["price"] == 8_000_000.0
    assert body["room_count"] == "3+1"
    assert body["listing_type"] == "sale"


def test_voice_draft_returns_503_when_not_configured(client, monkeypatch):
    headers = _register(client, "Ofis Voice Test 2", "owner2@voice-test.com")

    def _raise(audio_bytes, content_type):
        raise voice_listing.VoiceListingError("__not_configured__")

    monkeypatch.setattr(listings_route, "transcribe_and_extract", _raise)

    resp = client.post(
        "/listings/voice-draft",
        files={"file": ("note.webm", io.BytesIO(b"fake-audio"), "audio/webm")},
        headers=headers,
    )
    assert resp.status_code == 503


def test_voice_draft_returns_502_on_model_error(client, monkeypatch):
    headers = _register(client, "Ofis Voice Test 3", "owner3@voice-test.com")

    def _raise(audio_bytes, content_type):
        raise voice_listing.VoiceListingError("Model yanıtı ayrıştırılamadı, tekrar deneyin.")

    monkeypatch.setattr(listings_route, "transcribe_and_extract", _raise)

    resp = client.post(
        "/listings/voice-draft",
        files={"file": ("note.webm", io.BytesIO(b"fake-audio"), "audio/webm")},
        headers=headers,
    )
    assert resp.status_code == 502


def test_voice_draft_rejects_empty_file(client):
    headers = _register(client, "Ofis Voice Test 4", "owner4@voice-test.com")
    resp = client.post(
        "/listings/voice-draft",
        files={"file": ("note.webm", io.BytesIO(b""), "audio/webm")},
        headers=headers,
    )
    assert resp.status_code == 422
