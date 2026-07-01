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


class LeadResponse(BaseModel):
    id: uuid.UUID
    source: str
    contact_phone: str
    district: str | None
    budget_min: float | None
    budget_max: float | None
    room_count: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MatchResult(BaseModel):
    listing_id: uuid.UUID
    title: str
    price: float
    match_reason: str
