import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_serializer

from app.core.storage import photo_proxy_url


class ListingCreate(BaseModel):
    title: str
    # city gönderilmezse route ilçe+mahalleden çıkarmayı dener (infer_city) —
    # portal aktarımı ve sesli not akışı şehir bilgisi vermeden de çalışır.
    city: str | None = None
    district: str
    neighborhood: str | None = None
    price: float
    room_count: str
    square_meters: int | None = None
    # Fiyat önerisi (Pricing Agent) emsalleri satılık/kiralık ayırmadan
    # karşılaştırınca anlamsız aralıklar üretiyordu — bkz. pricing.py.
    listing_type: Literal["sale", "rent"] = "sale"
    # Oda sayısının anlamsız olduğu ticari/arsa ilanlarında Matching Agent
    # room_count filtresini atlamak için kullanılır (bkz. app/agents/matching.py).
    property_type: Literal["residential", "commercial", "land"] = "residential"


class ListingResponse(BaseModel):
    id: uuid.UUID
    title: str
    city: str | None = None
    district: str
    neighborhood: str | None = None
    price: float
    room_count: str
    square_meters: int | None
    listing_type: str
    property_type: str
    status: str
    photos: list[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("photos")
    def _serialize_photos(self, photos: list[str]) -> list[str]:
        # DB'de bare S3 key saklanıyor (bucket private olduğu için public URL değil);
        # burada backend proxy route'una işaret eden gerçek URL'e çevriliyor.
        return [photo_proxy_url(key) for key in photos]


class ListingUpdate(BaseModel):
    # Tüm alanlar opsiyonel — route model_dump(exclude_unset=True) ile sadece
    # gönderilen alanları uygular, diğerlerini olduğu gibi bırakır.
    title: str | None = None
    city: str | None = None
    district: str | None = None
    neighborhood: str | None = None
    price: float | None = None
    room_count: str | None = None
    square_meters: int | None = None


class ListingStatusUpdate(BaseModel):
    status: str


class ListingTypeUpdate(BaseModel):
    listing_type: Literal["sale", "rent"]


class ListingPropertyTypeUpdate(BaseModel):
    property_type: Literal["residential", "commercial", "land"]


class ListingPhotoFromUrlRequest(BaseModel):
    url: str


class ListingExtractRequest(BaseModel):
    url: str


class ListingExtractFromHtmlRequest(BaseModel):
    html: str


class StoreImportRequest(BaseModel):
    # Sahibinden mağaza adresi, örn. "toycuemlak.sahibinden.com" (şema opsiyonel).
    url: str


class ListingExtractResponse(BaseModel):
    title: str | None
    # Portal kaynağında şehir çoğunlukla yoktur — parser ilçe+mahalle
    # eşleşmesinden çıkarır (bkz. app/core/geo.py: resolve_location).
    city: str | None = None
    district: str | None
    neighborhood: str | None = None
    price: float | None
    room_count: str | None
    square_meters: int | None
    # Sadece best-effort bir öneri — danışman inceleme ekranında değiştirebilir,
    # tespit edilemezse None (formda varsayılan "sale" seçili gelir).
    listing_type: Literal["sale", "rent"] | None = None
    property_type: Literal["residential", "commercial", "land"] | None = None
    cover_photo_url: str | None = None


class ListingPortfolioExtractResponse(BaseModel):
    listings: list[ListingExtractResponse]


class VoiceListingDraftResponse(BaseModel):
    transcript: str
    title: str | None
    district: str | None
    price: float | None
    room_count: str | None
    square_meters: int | None
    listing_type: Literal["sale", "rent"] | None = None
    property_type: Literal["residential", "commercial", "land"] | None = None
