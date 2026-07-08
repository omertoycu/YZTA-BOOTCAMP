from pydantic import BaseModel


class DistrictCount(BaseModel):
    district: str
    count: int


class DistrictRevenue(BaseModel):
    district: str
    revenue: float


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
    # Komisyon takibi (bkz. PATCH /leads/{id}/deal) — status="won" şartı aranmaz,
    # danışman anlaşma detayını status geçişinden bağımsız girebilir.
    conversion_rate: float | None
    closed_deal_count: int
    total_deal_volume: float
    total_revenue: float
    average_commission: float | None
    revenue_by_district: list[DistrictRevenue]
