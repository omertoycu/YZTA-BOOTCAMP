"""WhatsApp otomatik yanıt katmanı (app/agents/whatsapp_bot.py) + webhook'tan
profil adı yakalama testleri. Bot tamamen opt-in (offices.auto_reply_enabled)
olduğu için mevcut intake testleri etkilenmez — buradaki testler bayrağı
açıkça set eder."""

import hashlib
import hmac
import json

from sqlalchemy import select

from app.agents import intake
from app.agents.whatsapp_bot import detect_command
from app.core.config import settings
from app.models.office import Office

WHATSAPP_APP_SECRET = "test-whatsapp-secret"


def _register_office(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "Supersecret123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _configure_office(db_session, office_name, phone_number_id, *, auto_reply=False, notification_phone=None):
    office = db_session.execute(select(Office).where(Office.name == office_name)).scalar_one()
    office.whatsapp_phone_number_id = phone_number_id
    office.auto_reply_enabled = auto_reply
    if notification_phone:
        office.notification_phone = notification_phone
    db_session.commit()


def _build_payload(
    phone_number_id, message_id, contact_phone, body="Merhaba, ilgileniyorum", profile_name=None
):
    value = {
        "metadata": {"phone_number_id": phone_number_id},
        "messages": [{"id": message_id, "from": contact_phone, "type": "text", "text": {"body": body}}],
    }
    if profile_name:
        value["contacts"] = [{"wa_id": contact_phone, "profile": {"name": profile_name}}]
    return {"entry": [{"changes": [{"value": value}]}]}


def _sign(body: bytes) -> str:
    digest = hmac.new(WHATSAPP_APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _post_webhook(client, payload):
    body = json.dumps(payload).encode()
    return client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": _sign(body)},
    )


# --- detect_command (saf birim testleri) ---


def test_detect_command_recognizes_variants():
    assert detect_command("MENÜ") == "menu"
    assert detect_command("menu") == "menu"
    assert detect_command("yardım") == "menu"
    assert detect_command("İLANLAR") == "listings"
    assert detect_command("portfoy") == "listings"
    assert detect_command("DURUM") == "status"
    assert detect_command("DANIŞMAN") == "agent"
    assert detect_command("danisman") == "agent"
    assert detect_command("  Danışman!! ") == "agent"


def test_detect_command_ignores_real_messages():
    assert detect_command("ilanlar hakkında bir sorum var") is None
    assert detect_command("Kadıköy'de 3+1 arıyorum") is None
    assert detect_command(None) is None
    assert detect_command("") is None


# --- Profil adı yakalama ---


def test_webhook_captures_whatsapp_profile_name(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", WHATSAPP_APP_SECRET)
    headers = _register_office(client, "Ofis Bot Ad Test 1", "owner@bot-ad-1.com")
    _configure_office(db_session, "Ofis Bot Ad Test 1", "2000000001")

    resp = _post_webhook(
        client,
        _build_payload("2000000001", "wamid.BOTAD1", "905552220001", profile_name="Ayşe Yılmaz"),
    )
    assert resp.status_code == 200

    leads = client.get("/leads", headers=headers).json()
    assert leads[0]["contact_name"] == "Ayşe Yılmaz"


def test_profile_name_does_not_overwrite_manual_name(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", WHATSAPP_APP_SECRET)
    headers = _register_office(client, "Ofis Bot Ad Test 2", "owner@bot-ad-2.com")
    _configure_office(db_session, "Ofis Bot Ad Test 2", "2000000002")

    client.post(
        "/leads",
        json={"contact_phone": "905552220002", "contact_name": "Mehmet Bey (asıl kayıt)"},
        headers=headers,
    )
    resp = _post_webhook(
        client,
        _build_payload("2000000002", "wamid.BOTAD2", "905552220002", profile_name="mehmet55"),
    )
    assert resp.status_code == 200

    leads = client.get("/leads", headers=headers).json()
    assert leads[0]["contact_name"] == "Mehmet Bey (asıl kayıt)"


# --- Otomatik yanıt (opt-in) ---


def test_no_auto_reply_when_flag_disabled(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", WHATSAPP_APP_SECRET)
    _register_office(client, "Ofis Bot Kapalı", "owner@bot-kapali.com")
    _configure_office(db_session, "Ofis Bot Kapalı", "2000000003", auto_reply=False)

    sent_calls = []
    monkeypatch.setattr(intake, "send_whatsapp_text", lambda *args: sent_calls.append(args))

    resp = _post_webhook(client, _build_payload("2000000003", "wamid.BOTOFF1", "905552220003"))
    assert resp.status_code == 200
    assert sent_calls == []  # ne karşılama ne başka bir bot mesajı


def test_new_lead_receives_welcome_with_usage_info(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", WHATSAPP_APP_SECRET)
    headers = _register_office(client, "Ofis Bot Karşılama", "owner@bot-karsilama.com")
    _configure_office(db_session, "Ofis Bot Karşılama", "2000000004", auto_reply=True)

    sent_calls = []
    monkeypatch.setattr(
        intake, "send_whatsapp_text", lambda pid, to, text: sent_calls.append((pid, to, text))
    )

    resp = _post_webhook(
        client,
        _build_payload("2000000004", "wamid.BOTWELCOME1", "905552220004", profile_name="Ali Veli"),
    )
    assert resp.status_code == 200
    assert len(sent_calls) == 1
    assert sent_calls[0][1] == "905552220004"
    assert "Ali Veli" in sent_calls[0][2]
    assert "İLANLAR" in sent_calls[0][2]
    assert "DANIŞMAN" in sent_calls[0][2]

    # Karşılama, konuşma geçmişine giden mesaj olarak da yazılmalı.
    lead_id = client.get("/leads", headers=headers).json()[0]["id"]
    messages = client.get(f"/leads/{lead_id}/messages", headers=headers).json()
    directions = [m["direction"] for m in messages]
    assert directions == ["in", "out"]


def test_menu_command_skips_extraction_and_replies(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", WHATSAPP_APP_SECRET)
    _register_office(client, "Ofis Bot Menü", "owner@bot-menu.com")
    _configure_office(db_session, "Ofis Bot Menü", "2000000005", auto_reply=True)

    def _fail_if_called(text):
        raise AssertionError("extract_lead_fields bir komut mesajı için çağrılmamalı")

    monkeypatch.setattr(intake, "extract_lead_fields", _fail_if_called)

    sent_calls = []
    monkeypatch.setattr(
        intake, "send_whatsapp_text", lambda pid, to, text: sent_calls.append((pid, to, text))
    )

    # İlk mesaj lead'i oluşturur (karşılama), ikincisi komut.
    _post_webhook(client, _build_payload("2000000005", "wamid.BOTMENU1", "905552220005", body="Selam"))
    _post_webhook(client, _build_payload("2000000005", "wamid.BOTMENU2", "905552220005", body="MENÜ"))

    assert len(sent_calls) == 2  # karşılama + menü yanıtı
    assert "Kısayollar" in sent_calls[1][2]


def test_new_lead_sending_menu_first_gets_single_welcome(client, db_session, monkeypatch):
    """Yeni bir aday ilk mesajı olarak doğrudan MENÜ yazarsa karşılama mesajı
    ile komut yanıtı aynı içerikte olduğu için tek mesaj gitmeli, iki kez
    aynı metin gönderilmemeli."""
    monkeypatch.setattr(settings, "whatsapp_app_secret", WHATSAPP_APP_SECRET)
    _register_office(client, "Ofis Bot Menü İlk", "owner@bot-menu-ilk.com")
    _configure_office(db_session, "Ofis Bot Menü İlk", "2000000009", auto_reply=True)

    sent_calls = []
    monkeypatch.setattr(
        intake, "send_whatsapp_text", lambda pid, to, text: sent_calls.append((pid, to, text))
    )

    _post_webhook(client, _build_payload("2000000009", "wamid.BOTMENUFIRST1", "905552220009", body="MENÜ"))

    assert len(sent_calls) == 1
    assert "Kısayollar" in sent_calls[0][2]


def test_agent_command_notifies_office(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", WHATSAPP_APP_SECRET)
    _register_office(client, "Ofis Bot Danışman", "owner@bot-danisman.com")
    _configure_office(
        db_session,
        "Ofis Bot Danışman",
        "2000000006",
        auto_reply=True,
        notification_phone="905559998888",
    )

    sent_calls = []
    monkeypatch.setattr(
        intake, "send_whatsapp_text", lambda pid, to, text: sent_calls.append((pid, to, text))
    )

    _post_webhook(
        client,
        _build_payload("2000000006", "wamid.BOTAGENT1", "905552220006", profile_name="Zeynep"),
    )
    sent_calls.clear()

    _post_webhook(client, _build_payload("2000000006", "wamid.BOTAGENT2", "905552220006", body="DANIŞMAN"))

    recipients = [call[1] for call in sent_calls]
    assert "905552220006" in recipients  # adaya onay yanıtı
    assert "905559998888" in recipients  # danışmana bildirim
    office_note = next(text for _, to, text in sent_calls if to == "905559998888")
    assert "Zeynep" in office_note


def test_criteria_message_triggers_auto_match_send(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", WHATSAPP_APP_SECRET)
    headers = _register_office(client, "Ofis Bot Eşleşme", "owner@bot-eslesme.com")
    _configure_office(db_session, "Ofis Bot Eşleşme", "2000000007", auto_reply=True)

    client.post(
        "/listings",
        json={"title": "Kadikoy 3+1 Satılık Daire", "district": "Kadikoy", "price": 4_500_000, "room_count": "3+1"},
        headers=headers,
    )

    def _fake_extract(text):
        return {
            "district": "Kadikoy",
            "budget_min": None,
            "budget_max": 5_000_000,
            "room_count": "3+1",
            "radius_km": None,
            "listing_type_preference": None,
            "property_type_preference": None,
        }

    monkeypatch.setattr(intake, "extract_lead_fields", _fake_extract)

    sent_calls = []
    monkeypatch.setattr(
        intake, "send_whatsapp_text", lambda pid, to, text: sent_calls.append((pid, to, text))
    )

    _post_webhook(
        client,
        _build_payload(
            "2000000007",
            "wamid.BOTMATCH1",
            "905552220007",
            body="Kadıköy'de 3+1 arıyorum, bütçem 5 milyon TL",
        ),
    )

    # Yeni lead, ilk mesajında zaten kriter veriyor: eskiden bu durumda
    # karşılama+kısayol mesajı hiç gitmiyordu (aday MENÜ/DANIŞMAN gibi
    # kısayolları hiç öğrenmiyordu) — artık her yeni temas, içerikten bağımsız
    # olarak sabit karşılama mesajını da alıyor, üstüne eşleşme mesajı gelir.
    assert len(sent_calls) == 2
    welcome_messages = [text for _, to, text in sent_calls if "İLANLAR" in text and "DANIŞMAN" in text]
    assert len(welcome_messages) == 1
    # Gemini yapılandırılmadığı için (test env) kişisel taslak yerine
    # deterministik listeye düşülür, gerçek portföy başlığı mesajda olmalı.
    match_messages = [text for _, to, text in sent_calls if "Kadikoy 3+1 Satılık Daire" in text]
    assert len(match_messages) == 1


def test_irrelevant_message_from_known_lead_gets_no_reply(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", WHATSAPP_APP_SECRET)
    _register_office(client, "Ofis Bot Sessiz", "owner@bot-sessiz.com")
    _configure_office(db_session, "Ofis Bot Sessiz", "2000000008", auto_reply=True)

    # Alan çıkarımı hiçbir şey bulamıyor (saçma mesaj senaryosu).
    monkeypatch.setattr(
        intake,
        "extract_lead_fields",
        lambda text: {field: None for field in intake.EXTRACTABLE_LEAD_FIELDS},
    )

    sent_calls = []
    monkeypatch.setattr(
        intake, "send_whatsapp_text", lambda pid, to, text: sent_calls.append((pid, to, text))
    )

    _post_webhook(client, _build_payload("2000000008", "wamid.BOTSILENT1", "905552220008", body="Merhaba"))
    sent_calls.clear()

    _post_webhook(
        client,
        _build_payload("2000000008", "wamid.BOTSILENT2", "905552220008", body="bugün hava çok güzel değil mi"),
    )
    assert sent_calls == []  # sessizlik = maliyet yok, yanlış beklenti yok
