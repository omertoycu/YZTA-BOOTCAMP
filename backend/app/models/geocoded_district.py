import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class GeocodedDistrict(Base):
    """Bölge adı -> koordinat önbelleği. Tenant verisi değil (offices gibi
    paylaşılan/global bir coğrafi gerçek), RLS policy'si yok."""

    __tablename__ = "geocoded_districts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    district_name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    geocoded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
