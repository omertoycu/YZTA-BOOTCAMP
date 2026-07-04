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
    # Satış hunisi: LEAD_STATUSES sırasıyla (new → ... → won/lost), 0'lar dahil.
    leads_by_status: dict[str, int]
    won_lead_count: int
    active_follow_up_count: int
    scored_lead_count: int
    average_score: float | None
    score_distribution: list[ScoreBucket]
