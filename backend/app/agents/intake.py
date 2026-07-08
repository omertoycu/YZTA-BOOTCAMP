from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agents.whatsapp_extract import (
    EXTRACTABLE_LEAD_FIELDS,
    WhatsAppExtractError,
    compute_new_extraction_counters,
    extract_lead_fields,
    should_run_extraction,
)
from app.agents.whatsapp_bot import build_auto_reply, detect_command
from app.agents.whatsapp_send import WhatsAppSendError, send_whatsapp_text
from app.core.db import set_tenant
from app.models.lead import Lead
from app.models.office import Office
from app.models.whatsapp_inbound_event import WhatsAppInboundEvent
from app.models.whatsapp_message import WhatsAppMessage

# Metin dışı mesaj tipleri için danışman panelinde gösterilecek placeholder —
# Gemini'ye hiç gönderilmez (extraction_text=None), sadece görünürlük için
# whatsapp_messages'a yazılır.
NON_TEXT_PLACEHOLDERS = {
    "image": "[Fotoğraf]",
    "audio": "[Ses kaydı]",
    "video": "[Video]",
    "document": "[Belge]",
    "location": "[Konum]",
    "sticker": "[Çıkartma]",
}
DEFAULT_PLACEHOLDER = "[Desteklenmeyen mesaj türü]"


class UnknownWhatsAppRecipientError(Exception):
    """Gelen webhook mesajının phone_number_id'si hiçbir ofise eşlenmemiş."""


def _resolve_message_body(message_type: str, text_body: str | None) -> tuple[str, str | None]:
    """(saklanacak gösterim metni, çıkarıma gönderilecek metin) döner. Metin
    dışı mesajlarda ikinci eleman None — extraction hiç tetiklenmez."""
    if message_type == "text" and text_body:
        return text_body, text_body
    return NON_TEXT_PLACEHOLDERS.get(message_type, DEFAULT_PLACEHOLDER), None


def resolve_office_id(db: Session, phone_number_id: str) -> str:
    """offices tablosunun RLS policy'si olmadığı için (bkz. migration 0005)
    bu sorgu, henüz hiçbir tenant context'i set edilmeden çalışabilir."""
    office = db.execute(
        select(Office).where(Office.whatsapp_phone_number_id == phone_number_id)
    ).scalar_one_or_none()
    if office is None:
        raise UnknownWhatsAppRecipientError(phone_number_id)
    return str(office.id)


def process_inbound_message(
    db: Session,
    office_id: str,
    external_message_id: str,
    contact_phone: str,
    message_type: str = "text",
    message_body: str | None = None,
    contact_name: str | None = None,
) -> Lead | None:
    """Gelen bir WhatsApp mesajını lead'e işler: var olan lead'i günceller ya da
    yeni lead oluşturur. Meta aynı mesajı en-az-bir-kez teslimat garantisiyle
    tekrar gönderebileceği için external_message_id daha önce işlendiyse hiçbir
    şey değiştirmeden None döner.
    """
    set_tenant(db, office_id)

    already_processed = db.execute(
        select(WhatsAppInboundEvent).where(
            WhatsAppInboundEvent.external_message_id == external_message_id
        )
    ).scalar_one_or_none()
    if already_processed is not None:
        return None

    lead = db.execute(
        select(Lead).where(Lead.office_id == office_id, Lead.contact_phone == contact_phone)
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)
    is_new_lead = lead is None
    if lead is None:
        lead = Lead(
            office_id=office_id,
            source="whatsapp",
            contact_phone=contact_phone,
            contact_name=contact_name,
            message_count=1,
            last_contacted_at=now,
        )
        db.add(lead)
        db.flush()
    else:
        lead.message_count += 1
        lead.last_contacted_at = now
        # WhatsApp profil adı sonradan görünür olabilir; danışmanın elle
        # girdiği bir isim varsa EZİLMEZ (fill-only, extraction ile aynı ilke).
        if contact_name and not lead.contact_name:
            lead.contact_name = contact_name
        # Aday yanıt verdi → otomatik takip zinciri durur, konuşmayı danışman
        # devralır (bkz. app/agents/follow_up.py). Zincir yeniden gerekirse
        # danışman panelden tekrar açar.
        if lead.auto_follow_up_enabled:
            lead.auto_follow_up_enabled = False
            lead.next_follow_up_at = None

    stored_body, extraction_text = _resolve_message_body(message_type, message_body)

    db.add(
        WhatsAppInboundEvent(
            office_id=office_id,
            lead_id=lead.id,
            external_message_id=external_message_id,
        )
    )
    db.add(
        WhatsAppMessage(
            office_id=office_id,
            lead_id=lead.id,
            direction="in",
            message_type=message_type,
            body=stored_body,
            external_message_id=external_message_id,
        )
    )

    try:
        db.commit()
    except IntegrityError:
        # İki webhook teslimatı aynı external_message_id ile yarıştıysa: ikincisi
        # unique constraint'e çarpar, sessizce yoksayılır (idempotency garantisi).
        db.rollback()
        return None

    if is_new_lead:
        _notify_new_lead(db, office_id, lead)

    # Tek kelimelik komutlar (MENÜ/İLANLAR/DURUM/DANIŞMAN) deterministik
    # yanıtlanır — Gemini alan çıkarımına hiç gönderilmez (maliyet kalkanı).
    command = detect_command(extraction_text)

    fields_updated = False
    if extraction_text and command is None:
        fields_updated = _maybe_extract_and_apply(db, office_id, lead, message_type, extraction_text)

    _maybe_auto_reply(
        db,
        office_id,
        lead,
        command=command,
        is_new_lead=is_new_lead,
        fields_updated=fields_updated,
    )

    return lead


def _notify_new_lead(db: Session, office_id: str, lead: Lead) -> None:
    """Yeni bir aday geldiğinde danışmana kendi WhatsApp'ından bir bildirim
    gönderir — panelden uzaktayken de haberdar olsun diye (ürünün "hiçbir
    fırsatı kaçırmama" vaadinin en kritik boşluğu). Best-effort: bildirim
    başarısız olsa da (örn. henüz yapılandırılmamış) webhook işlemi zaten
    tamamlanmış, aday kaydı bundan etkilenmez."""
    office = db.get(Office, office_id)
    if not office or not office.notification_phone or not office.whatsapp_phone_number_id:
        return

    message = (
        f"Yeni bir aday geldi: {lead.contact_phone}"
        f"{f' ({lead.district})' if lead.district else ''}. "
        "Panelden görüntüleyip yanıtlayabilirsiniz."
    )
    try:
        send_whatsapp_text(office.whatsapp_phone_number_id, office.notification_phone, message)
    except WhatsAppSendError:
        pass


def _maybe_extract_and_apply(
    db: Session, office_id: str, lead: Lead, message_type: str, message_body: str
) -> bool:
    """Best-effort: Gemini hatası (yapılandırma eksik, ağ hatası, geçersiz
    yanıt) hiçbir exception dışarı sızdırmaz, webhook her koşulda 200 döner.
    Ayrı transaction: ana commit SET LOCAL tenant context'ini sıfırladığı için
    (bkz. CLAUDE.md madde 2/7) set_tenant BURADA TEKRAR çağrılmalı — ama lead
    NESNESİ yeniden SELECT edilmeye gerek yok (expire_on_commit=False, aynı
    session'da hâlâ geçerli, bkz. _notify_new_lead'in aynı deseni).

    Dönüş değeri: bu mesajla en az bir alan dolduysa True — otomatik yanıt
    katmanı (bkz. _maybe_auto_reply) eşleşme gönderimini buna bağlar."""
    set_tenant(db, office_id)

    if not should_run_extraction(
        message_type=message_type,
        message_body=message_body,
        district=lead.district,
        budget_max=lead.budget_max,
        room_count=lead.room_count,
        extraction_count=lead.llm_extraction_count,
        last_extraction_at=lead.last_llm_extraction_at,
    ):
        db.rollback()  # set_tenant'ın açtığı boş transaction'ı kapat
        return False

    now = datetime.now(timezone.utc)
    try:
        extracted = extract_lead_fields(message_body)
    except WhatsAppExtractError as exc:
        if str(exc) == "__not_configured__":
            db.rollback()  # hiç Gemini çağrısı yapılmadı, sayaç işletilmez
            return False
        lead.llm_extraction_count, lead.last_llm_extraction_at = compute_new_extraction_counters(
            lead.llm_extraction_count, lead.last_llm_extraction_at, now
        )
        db.commit()  # başarısız ama maliyetli deneme yine de sayılır
        return False

    lead.llm_extraction_count, lead.last_llm_extraction_at = compute_new_extraction_counters(
        lead.llm_extraction_count, lead.last_llm_extraction_at, now
    )
    filled_any = False
    for field in EXTRACTABLE_LEAD_FIELDS:
        if getattr(lead, field) is None and extracted.get(field) is not None:
            setattr(lead, field, extracted[field])
            filled_any = True
    if filled_any:
        lead.fields_extracted_by_ai = True

    db.commit()
    return filled_any


def _maybe_auto_reply(
    db: Session,
    office_id: str,
    lead: Lead,
    *,
    command: str | None,
    is_new_lead: bool,
    fields_updated: bool,
) -> None:
    """Opt-in otomatik yanıt (bkz. app/agents/whatsapp_bot.py): ofis
    auto_reply_enabled değilse hiçbir şey yapılmaz. Best-effort — yanıt
    üretimi/gönderimi başarısız olsa da webhook işlemi zaten tamamlanmıştır.
    Ayrı transaction: bir önceki commit tenant context'ini sıfırladığı için
    set_tenant burada yeniden çağrılır (Matching Agent RLS'li listings'i okur)."""
    office = db.get(Office, office_id)
    if not office or not office.auto_reply_enabled or not office.whatsapp_phone_number_id:
        db.rollback()  # db.get'in açtığı boş transaction'ı kapat
        return

    set_tenant(db, office_id)
    replies = build_auto_reply(
        db,
        office,
        lead,
        command=command,
        is_new_lead=is_new_lead,
        fields_updated=fields_updated,
    )
    if not replies:
        db.rollback()
        return

    # Birden fazla mesaj olabilir (örn. yeni adaya karşılama + aynı mesajdan
    # gelen kriterlerle eşleşme gönderimi) — sırayla gönderilir, ilk hatada
    # durulur ama o ana kadar başarıyla gidenler yine de commit edilir.
    sent_any = False
    for reply in replies:
        try:
            send_whatsapp_text(office.whatsapp_phone_number_id, lead.contact_phone, reply)
        except WhatsAppSendError:
            break
        db.add(
            WhatsAppMessage(
                office_id=office_id, lead_id=lead.id, direction="out", message_type="text", body=reply
            )
        )
        sent_any = True

    if sent_any:
        db.commit()
    else:
        db.rollback()

    # Aday DANIŞMAN yazdıysa danışmana da haber uçur — "hiçbir fırsatı
    # kaçırma" vaadinin en sıcak anı, best-effort (_notify_new_lead deseni).
    if command == "agent" and office.notification_phone:
        who = f"{lead.contact_name} ({lead.contact_phone})" if lead.contact_name else lead.contact_phone
        try:
            send_whatsapp_text(
                office.whatsapp_phone_number_id,
                office.notification_phone,
                f"{who} sizinle görüşmek istiyor (WhatsApp'ta DANIŞMAN yazdı). "
                "En kısa sürede dönüş yapmanız önerilir.",
            )
        except WhatsAppSendError:
            pass
