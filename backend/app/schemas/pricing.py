from pydantic import BaseModel


class PricingSuggestionResponse(BaseModel):
    has_enough_data: bool
    comparable_count: int
    message: str | None = None
    suggested_min: float | None = None
    suggested_max: float | None = None
    comparables: list[dict]
