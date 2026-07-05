import uuid

from pydantic import BaseModel


class PricingSuggestionResponse(BaseModel):
    has_enough_data: bool
    comparable_count: int
    message: str | None = None
    suggested_min: float | None = None
    suggested_max: float | None = None
    comparables: list[dict]


class StaleListingAlert(BaseModel):
    listing_id: uuid.UUID
    title: str
    district: str
    price: float
    age_days: int
    suggested_max: float
    overprice_pct: float
    message: str
