from pydantic import BaseModel


class DistrictCount(BaseModel):
    district: str
    count: int


class ScoreBucket(BaseModel):
    label: str
    count: int


class ReportsOverviewResponse(BaseModel):
    listing_count: int
    active_listing_count: int
    listings_by_district: list[DistrictCount]
    lead_count: int
    leads_by_source: dict[str, int]
    leads_by_district: list[DistrictCount]
    scored_lead_count: int
    average_score: float | None
    score_distribution: list[ScoreBucket]
