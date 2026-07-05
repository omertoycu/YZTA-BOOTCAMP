import uuid
from datetime import datetime

from sqlalchemy import Boolean, Integer, String, Numeric, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    office_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("offices.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(30), default="manual")  # whatsapp | manual
    # Satış hunisi aşaması: new → contacted → viewing → negotiation → won/lost
    # (bkz. app/api/routes/leads.py: LEAD_STATUSES)
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    district: Mapped[str] = mapped_column(String(120), nullable=True)
    budget_min: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    budget_max: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    room_count: Mapped[str] = mapped_column(String(20), nullable=True)
    # Set edilirse matching_node district tam eşleşmesi yerine bu yarıçapta
    # coğrafi filtre uygular (bkz. app/agents/geocoding.py, app/agents/matching.py).
    radius_km: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    # message_count/last_contacted_at manuel girişte elle, WhatsApp Intake Agent'ında
    # (app/agents/intake.py) otomatik güncellenir. Mesaj içeriği/transkript ayrı bir
    # tabloda tutulmuyor — sadece idempotency için whatsapp_inbound_events var.
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Otomatik WhatsApp takip zinciri (bkz. app/agents/follow_up.py): danışman
    # açar, scheduler vadesi gelen aşamayı gönderir, lead yanıt verince
    # (app/agents/intake.py) zincir kendiliğinden durur.
    auto_follow_up_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    follow_up_stage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Danışmanın kendine bıraktığı kişisel hatırlatma (örn. sesli not agent'ının
    # önerdiği "cuma günü tekrar ara") — otomatik WhatsApp takip zincirinden
    # (yukarıdaki auto_follow_up_*/next_follow_up_at) tamamen bağımsız, adaya
    # hiçbir otomatik mesaj gitmez, sadece panelde danışmana görünür.
    reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Yer gösterme randevusu (bkz. app/agents/calendar_invite.py, app/agents/
    # appointment_reminder.py): somut bir tarih/saat + konum. reminder_at/note'tan
    # (yukarıda) farklı — bu bir TAKVİM randevusu, .ics üretilebilir ve randevudan
    # 24 saat önce otomatik bir WhatsApp hatırlatması tetikler (appointment_reminder_sent
    # bunun bir kez gönderilmesini garanti eder).
    appointment_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    appointment_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    appointment_reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
