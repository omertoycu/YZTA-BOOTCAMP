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
    # Set edilirse eşleştirmede bölge tam eşleşmesi yerine coğrafi yarıçap
    # filtresi uygulanır (bkz. app/agents/matching.py).
    radius_km: float | None = None
    # WhatsApp Intake Agent gelene kadar (Sprint 2), bu ikisi manuel/demo amaçlı
    # elle girilir; gerçek konuşma verisi geldiğinde otomatik güncellenecek.
    message_count: int = 0
    last_contacted_at: datetime | None = None


class LeadResponse(BaseModel):
    id: uuid.UUID
    source: str
    status: str
    contact_phone: str
    district: str | None
    budget_min: float | None
    budget_max: float | None
    room_count: str | None
    radius_km: float | None
    message_count: int
    last_contacted_at: datetime | None
    auto_follow_up_enabled: bool
    follow_up_stage: int
    next_follow_up_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MatchResult(BaseModel):
    listing_id: uuid.UUID
    title: str
    price: float
    match_reason: str


class FollowUpRequest(BaseModel):
    message: str | None = None


class AutoFollowUpRequest(BaseModel):
    enabled: bool


class LeadStatusUpdate(BaseModel):
    status: str


class LeadNoteCreate(BaseModel):
    body: str


class LeadNoteResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    author_id: uuid.UUID
    author_email: str | None = None
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SendMatchesResponse(BaseModel):
    sent: bool
    match_count: int
    message: str


class FollowUpResponse(BaseModel):
    sent: bool
    message: str
