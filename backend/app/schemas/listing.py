import uuid
from datetime import datetime

from pydantic import BaseModel, field_serializer

from app.core.storage import photo_proxy_url


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

    @field_serializer("photos")
    def _serialize_photos(self, photos: list[str]) -> list[str]:
        # DB'de bare S3 key saklanıyor (bucket private olduğu için public URL değil);
        # burada backend proxy route'una işaret eden gerçek URL'e çevriliyor.
        return [photo_proxy_url(key) for key in photos]


class ListingStatusUpdate(BaseModel):
    status: str


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


class ListingPortfolioExtractResponse(BaseModel):
    listings: list[ListingExtractResponse]


class LocationReportRequest(BaseModel):
    target_address: str
    target_label: str | None = None


class VoiceListingDraftResponse(BaseModel):
    transcript: str
    title: str | None
    district: str | None
    price: float | None
    room_count: str | None
    square_meters: int | None
