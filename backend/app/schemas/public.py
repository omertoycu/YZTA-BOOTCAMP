import uuid
from datetime import datetime

from pydantic import BaseModel, field_serializer

from app.core.storage import photo_proxy_url


class PublicListingResponse(BaseModel):
    id: uuid.UUID
    title: str
    city: str | None = None
    district: str
    neighborhood: str | None = None
    price: float
    room_count: str
    square_meters: int | None
    photos: list[str] = []
    office_name: str

    model_config = {"from_attributes": True}

    @field_serializer("photos")
    def _serialize_photos(self, photos: list[str]) -> list[str]:
        return [photo_proxy_url(key) for key in photos]


class ListingViewStatsResponse(BaseModel):
    view_count: int
    last_viewed_at: datetime | None
