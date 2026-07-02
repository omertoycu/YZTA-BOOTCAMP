import uuid
from datetime import datetime

from pydantic import BaseModel


class LeadCreate(BaseModel):
    contact_phone: str
    source: str = "manual"
    district: str | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    room_count: str | None = None
    # WhatsApp Intake Agent gelene kadar (Sprint 2), bu ikisi manuel/demo amaçlı
    # elle girilir; gerçek konuşma verisi geldiğinde otomatik güncellenecek.
    message_count: int = 0
    last_contacted_at: datetime | None = None


class LeadResponse(BaseModel):
    id: uuid.UUID
    source: str
    contact_phone: str
    district: str | None
    budget_min: float | None
    budget_max: float | None
    room_count: str | None
    message_count: int
    last_contacted_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MatchResult(BaseModel):
    listing_id: uuid.UUID
    title: str
    price: float
    match_reason: str
