from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.whatsapp_send import WhatsAppSendError, send_whatsapp_text
from app.core.config import settings
from app.core.db import set_tenant
from app.models.lead import Lead
from app.models.office import Office
from app.models.whatsapp_message import WhatsAppMessage

# Otomatik takip zinciri: (bir önceki temastan ne kadar sonra, mesaj şablonu).
# Aşama mesajları giderek daha az ısrarcı — üçüncüden sonra zincir kendini kapatır,
# aday sonsuza kadar mesaj almaz.
FOLLOW_UP_CHAIN: list[tuple[timedelta, str]] = [
    (
        timedelta(days=1),
        "Merhaba, PortföyAI danışmanınız buradan yazıyor. {district} için aradığınız "
        "kriterlere uygun portföylerimizi sizin için takip ediyorum, uygun olduğunuzda "
        "görüşebilir miyiz?",
    ),
    (
        timedelta(days=3),
        "Merhaba, tekrar ben. {district} tarafında kriterlerinize uyabilecek yeni "
        "seçenekler oldu — kısa bir telefon görüşmesi için müsait olduğunuz bir zaman var mı?",
    ),
    (
        timedelta(days=7),
        "Merhaba, son bir kez yazmak istedim. Arayışınız devam ediyorsa memnuniyetle "
        "yardımcı olurum; dilerseniz bu numaradan bana her zaman ulaşabilirsiniz. İyi günler dilerim.",
    ),
]


def enable_auto_follow_up(lead: Lead, now: datetime | None = None) -> None:
    """Zinciri baştan başlatır: ilk mesaj, ilk aşamanın gecikmesi kadar sonra gider."""
    now = now or datetime.now(timezone.utc)
    lead.auto_follow_up_enabled = True
    lead.follow_up_stage = 0
    lead.next_follow_up_at = now + FOLLOW_UP_CHAIN[0][0]


def disable_auto_follow_up(lead: Lead) -> None:
    lead.auto_follow_up_enabled = False
    lead.next_follow_up_at = None


def run_due_follow_ups(db: Session, now: datetime | None = None) -> dict:
    """Vadesi gelen tüm takip mesajlarını gönderir (tüm ofisler için).

    Cron tarafından tetiklenir (bkz. POST /internal/run-follow-ups). RLS'li
    leads tablosunu ofis ofis dolaşır: her ofis için tenant context set edilip
    o ofisin vadesi gelen lead'leri işlenir. commit SET LOCAL'ı sıfırladığı
    için (bkz. CLAUDE.md madde 2) her ofis kendi transaction'ında işlenir ve
    bir sonraki ofis için context yeniden set edilir.

    Gönderim başarısız olursa aşama İLERLETİLMEZ — bir sonraki cron
    çalışmasında aynı mesaj yeniden denenir (en-az-bir-kez semantiği; Meta
    tarafında spam'e dönmemesi için cron aralığı saatler mertebesinde olmalı).
    """
    now = now or datetime.now(timezone.utc)
    summary = {"offices": 0, "sent": 0, "failed": 0}

    if not settings.whatsapp_token:
        # WhatsApp hiç bağlı değilken her lead'i tek tek deneyip hata saymak
        # anlamsız; cron yine 200 alır, sadece hiçbir şey gönderilmediğini görür.
        summary["detail"] = "whatsapp_not_configured"
        return summary

    # offices tablosu RLS'siz/global (bkz. migration 0005) — tenant context'i
    # olmadan okunabilir. Sadece WhatsApp'ı bağlı ofisler taranır.
    offices = (
        db.execute(select(Office).where(Office.whatsapp_phone_number_id.is_not(None))).scalars().all()
    )

    for office in offices:
        set_tenant(db, str(office.id))
        due_leads = (
            db.execute(
                select(Lead).where(
                    Lead.auto_follow_up_enabled.is_(True),
                    Lead.next_follow_up_at.is_not(None),
                    Lead.next_follow_up_at <= now,
                )
            )
            .scalars()
            .all()
        )
        if not due_leads:
            db.rollback()  # set_tenant'ın açtığı boş transaction'ı kapat
            continue

        summary["offices"] += 1
        for lead in due_leads:
            stage = lead.follow_up_stage
            if stage >= len(FOLLOW_UP_CHAIN):
                # Normalde son mesaj gönderilirken zincir kapanır; bu satıra
                # sadece tutarsız veri (elle müdahale vb.) ile düşülür.
                disable_auto_follow_up(lead)
                continue

            message = FOLLOW_UP_CHAIN[stage][1].format(district=lead.district or "aradığınız bölge")
            try:
                send_whatsapp_text(office.whatsapp_phone_number_id, lead.contact_phone, message)
            except WhatsAppSendError:
                summary["failed"] += 1
                continue

            lead.follow_up_stage = stage + 1
            lead.last_contacted_at = now
            if lead.follow_up_stage >= len(FOLLOW_UP_CHAIN):
                disable_auto_follow_up(lead)
            else:
                lead.next_follow_up_at = now + FOLLOW_UP_CHAIN[lead.follow_up_stage][0]
            db.add(
                WhatsAppMessage(
                    office_id=office.id, lead_id=lead.id, direction="out", message_type="text", body=message
                )
            )
            summary["sent"] += 1

        db.commit()

    return summary
