import uuid
from datetime import datetime
from typing import Literal

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
    # None = belirtilmedi/fark etmez — Matching Agent bu durumda filtre
    # uygulamaz (bkz. app/agents/matching.py).
    listing_type_preference: Literal["sale", "rent"] | None = None
    property_type_preference: Literal["residential", "commercial", "land"] | None = None
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
    listing_type_preference: str | None
    property_type_preference: str | None
    message_count: int
    last_contacted_at: datetime | None
    auto_follow_up_enabled: bool
    follow_up_stage: int
    next_follow_up_at: datetime | None
    reminder_at: datetime | None
    reminder_note: str | None
    appointment_at: datetime | None
    appointment_location: str | None
    deal_amount: float | None
    commission_amount: float | None
    deal_closed_at: datetime | None
    fields_extracted_by_ai: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadUpdate(BaseModel):
    district: str | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    room_count: str | None = None
    radius_km: float | None = None
    listing_type_preference: Literal["sale", "rent"] | None = None
    property_type_preference: Literal["residential", "commercial", "land"] | None = None


class WhatsAppMessageResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    direction: str
    message_type: str
    body: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadFieldExtractionDraft(BaseModel):
    district: str | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    room_count: str | None = None
    radius_km: float | None = None
    listing_type_preference: Literal["sale", "rent"] | None = None
    property_type_preference: Literal["residential", "commercial", "land"] | None = None


class SuggestReplyResponse(BaseModel):
    draft: str
    match_count: int


class MatchResult(BaseModel):
    listing_id: uuid.UUID
    title: str
    price: float
    match_reason: str
    # AI yeniden sıralama (bkz. app/agents/match_ranking.py) çalışmazsa
    # (yapılandırılmamış/hata) None kalır — frontend bu durumda göstermez.
    relevance_score: int | None = None


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


class LeadVoiceNoteDraftResponse(BaseModel):
    transcript: str
    note_summary: str | None
    suggested_status: str | None
    reminder_at: datetime | None
    reminder_note: str | None


class LeadReminderUpdate(BaseModel):
    reminder_at: datetime | None = None
    reminder_note: str | None = None


class AppointmentCreate(BaseModel):
    appointment_at: datetime
    location: str
    send_whatsapp_confirmation: bool = True


class AppointmentResponse(BaseModel):
    lead: LeadResponse
    whatsapp_confirmation_sent: bool
    whatsapp_confirmation_error: str | None = None


class DealUpdate(BaseModel):
    deal_amount: float | None = None
    commission_amount: float | None = None
    deal_closed_at: datetime | None = None
