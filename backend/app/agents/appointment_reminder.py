from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.whatsapp_send import WhatsAppSendError, send_whatsapp_text
from app.core.config import settings
from app.core.db import set_tenant
from app.models.lead import Lead
from app.models.office import Office
from app.models.whatsapp_message import WhatsAppMessage

# Randevudan bu kadar önce, tek seferlik bir hatırlatma gönderilir. Takip
# zincirinden (follow_up.py) tamamen ayrı — no-show'u azaltmayı hedefler.
REMINDER_WINDOW = timedelta(hours=24)


def run_due_appointment_reminders(db: Session, now: datetime | None = None) -> dict:
    """Randevusuna 24 saatten az kalan ve daha önce hatırlatma gönderilmemiş
    adaylara tek seferlik bir WhatsApp hatırlatması gönderir. Cron tarafından
    tetiklenir (bkz. POST /internal/run-appointment-reminders) — otomatik takip
    zincirininkiyle (follow_up.py: run_due_follow_ups) aynı ofis-ofis dolaşma
    ve tenant context deseni kullanılır (bkz. CLAUDE.md madde 2/7: SET LOCAL
    commit'te sıfırlanır, her ofis kendi transaction'ında işlenir)."""
    now = now or datetime.now(timezone.utc)
    summary = {"offices": 0, "sent": 0, "failed": 0}

    if not settings.whatsapp_token:
        summary["detail"] = "whatsapp_not_configured"
        return summary

    offices = (
        db.execute(select(Office).where(Office.whatsapp_phone_number_id.is_not(None))).scalars().all()
    )

    for office in offices:
        set_tenant(db, str(office.id))
        due_leads = (
            db.execute(
                select(Lead).where(
                    Lead.appointment_at.is_not(None),
                    Lead.appointment_reminder_sent.is_(False),
                    Lead.appointment_at > now,
                    Lead.appointment_at <= now + REMINDER_WINDOW,
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
            local_time = lead.appointment_at.strftime("%d.%m.%Y %H:%M")
            location_part = f" ({lead.appointment_location})" if lead.appointment_location else ""
            message = (
                f"Hatırlatma: {local_time} saatinde{location_part} yer gösterimi randevunuz var. "
                "Görüşmek üzere!"
            )
            try:
                send_whatsapp_text(office.whatsapp_phone_number_id, lead.contact_phone, message)
            except WhatsAppSendError:
                summary["failed"] += 1
                continue

            lead.appointment_reminder_sent = True
            db.add(
                WhatsAppMessage(
                    office_id=office.id, lead_id=lead.id, direction="out", message_type="text", body=message
                )
            )
            summary["sent"] += 1

        db.commit()

    return summary
