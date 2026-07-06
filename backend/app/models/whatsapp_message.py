import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class WhatsAppMessage(Base):
    """Danışman panelinde gösterilecek WhatsApp konuşma geçmişi (bkz. GET
    /leads/{id}/messages). whatsapp_inbound_events'ten (sadece idempotency,
    mesaj metni tutmaz) farklı: bu tablo görüntülenebilir içerik tutar, hem
    gelen (in) hem giden (out) mesajlar için."""

    __tablename__ = "whatsapp_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    office_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("offices.id"), nullable=False)
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # in | out
    message_type: Mapped[str] = mapped_column(String(20), default="text")
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
