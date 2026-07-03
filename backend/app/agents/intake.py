from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import set_tenant
from app.models.lead import Lead
from app.models.office import Office
from app.models.whatsapp_inbound_event import WhatsAppInboundEvent


class UnknownWhatsAppRecipientError(Exception):
    """Gelen webhook mesajının phone_number_id'si hiçbir ofise eşlenmemiş."""


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
    if lead is None:
        lead = Lead(
            office_id=office_id,
            source="whatsapp",
            contact_phone=contact_phone,
            message_count=1,
            last_contacted_at=now,
        )
        db.add(lead)
        db.flush()
    else:
        lead.message_count += 1
        lead.last_contacted_at = now

    db.add(
        WhatsAppInboundEvent(
            office_id=office_id,
            lead_id=lead.id,
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

    return lead
