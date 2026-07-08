import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Office(Base):
    __tablename__ = "offices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subscription_plan: Mapped[str] = mapped_column(String(50), default="starter")
    # Meta Cloud API webhook'unu bu ofise yönlendirmek için kullanılır (bkz.
    # app/agents/intake.py). WhatsApp Business doğrulaması tamamlanana kadar boş kalır.
    whatsapp_phone_number_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    # Danışmanın kendi WhatsApp numarası — yeni lead geldiğinde bildirim buraya
    # gider (bkz. app/agents/intake.py: _notify_new_lead). whatsapp_phone_number_id
    # gönderim tarafı (Meta Graph API kimliği), bu ALIM tarafı (gerçek telefon numarası).
    notification_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Opt-in: açıkken WhatsApp Intake Agent gelen mesajlara ofis adına otomatik
    # yanıt verir (karşılama/komutlar + kriter dolunca eşleşen portföyler,
    # bkz. app/agents/whatsapp_bot.py). Varsayılan kapalı.
    auto_reply_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Ofis logosu — listings.photos ile aynı desende bare S3 nesne anahtarı
    # (bucket private, sunum GET /offices/logo/{key} proxy'siyle).
    logo_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
