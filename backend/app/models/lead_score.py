import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class LeadScore(Base):
    __tablename__ = "lead_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    office_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("offices.id"), nullable=False)
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100
    score_breakdown: Mapped[dict] = mapped_column(JSONB, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
