import uuid

from pydantic import BaseModel


class PricingSuggestionResponse(BaseModel):
    has_enough_data: bool
    comparable_count: int
    message: str | None = None
    suggested_min: float | None = None
    suggested_max: float | None = None
    comparables: list[dict]


class MarketSource(BaseModel):
    title: str
    url: str


class MarketPriceCheckResponse(BaseModel):
    has_market_data: bool
    estimated_min: float | None = None
    estimated_max: float | None = None
    summary: str | None = None
    sources: list[MarketSource] = []


class StaleListingAlert(BaseModel):
    listing_id: uuid.UUID
    title: str
    district: str
    price: float
    age_days: int
    suggested_max: float
    overprice_pct: float
    message: str
