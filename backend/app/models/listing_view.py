import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ListingView(Base):
    __tablename__ = "listing_views"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    office_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("offices.id"), nullable=False)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False)
    # Bilinçli olarak server_default=func.now() DEĞİL, Python-side default: bu
    # sütun DB'de server-generated olarak işaretlenirse SQLAlchemy ORM'i INSERT'e
    # otomatik bir RETURNING ekler, bu da portfoyai_public rolünün (sadece INSERT,
    # SELECT'i yok — bkz. migration 0013) INSERT'ini "RLS policy'sini ihlal
    # ediyor" hatasıyla reddetmesine yol açar (RETURNING, RLS'in SELECT tarafını
    # da tetikler). Python-side default ile hiç RETURNING'e gerek kalmaz.
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
