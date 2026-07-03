import uuid
from datetime import datetime

from pydantic import BaseModel


class ListingCreate(BaseModel):
    title: str
    district: str
    price: float
    room_count: str
    square_meters: int | None = None


class ListingResponse(BaseModel):
    id: uuid.UUID
    title: str
    district: str
    price: float
    room_count: str
    square_meters: int | None
    status: str
    photos: list[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ListingExtractRequest(BaseModel):
    url: str


class ListingExtractFromHtmlRequest(BaseModel):
    html: str


class ListingExtractResponse(BaseModel):
    title: str | None
    district: str | None
    price: float | None
    room_count: str | None
    square_meters: int | None


class VoiceListingDraftResponse(BaseModel):
    transcript: str
    title: str | None
    district: str | None
    price: float | None
    room_count: str | None
    square_meters: int | None
