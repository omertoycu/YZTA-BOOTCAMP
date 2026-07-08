from typing import TypedDict


class AgentState(TypedDict, total=False):
    office_id: str
    lead_id: str
    budget_min: float | None
    budget_max: float | None
    room_count: str | None
    district: str | None
    radius_km: float | None
    listing_type_preference: str | None
    property_type_preference: str | None
    candidate_listings: list[dict]
