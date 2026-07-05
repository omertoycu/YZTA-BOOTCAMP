from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.leads import LEAD_STATUSES
from app.middleware.tenant import get_tenant_db
from app.models.lead import Lead
from app.models.lead_score import LeadScore
from app.models.listing import Listing
from app.schemas.reports import DistrictCount, DistrictRevenue, ReportsOverviewResponse, ScoreBucket

router = APIRouter(prefix="/reports", tags=["reports"])

SCORE_BUCKET_ORDER = ["Yüksek (70-100)", "Orta (40-69)", "Düşük (0-39)"]


def _bucket_label(score: int) -> str:
    if score >= 70:
        return "Yüksek (70-100)"
    if score >= 40:
        return "Orta (40-69)"
    return "Düşük (0-39)"


@router.get("/overview", response_model=ReportsOverviewResponse)
def get_overview(db: Session = Depends(get_tenant_db)):
    # RLS, current_user'ın office_id'si dışındaki satırları zaten filtreler.
    listings = db.execute(select(Listing)).scalars().all()
    leads = db.execute(select(Lead)).scalars().all()

    # Her lead'in en güncel skorunu al (computed_at artan sırada işlenip
    # üzerine yazılır, o yüzden son yazılan en güncel skor kalır).
    latest_score_by_lead: dict = {}
    scores_query = select(LeadScore).order_by(LeadScore.computed_at)
    for score in db.execute(scores_query).scalars().all():
        latest_score_by_lead[score.lead_id] = score.score

    listing_district_counts = Counter(listing.district for listing in listings if listing.district)
    lead_district_counts = Counter(lead.district for lead in leads if lead.district)
    source_counts = Counter(lead.source for lead in leads)
    status_counts = Counter(lead.status for lead in leads)

    scores = list(latest_score_by_lead.values())
    bucket_counts = Counter(_bucket_label(score) for score in scores)

    closed_deals = [lead for lead in leads if lead.commission_amount is not None]
    total_revenue = sum(float(lead.commission_amount) for lead in closed_deals)
    total_deal_volume = sum(float(lead.deal_amount) for lead in leads if lead.deal_amount is not None)
    revenue_by_district: Counter = Counter()
    for lead in closed_deals:
        if lead.district:
            revenue_by_district[lead.district] += float(lead.commission_amount)

    return ReportsOverviewResponse(
        listing_count=len(listings),
        active_listing_count=sum(1 for listing in listings if listing.status == "active"),
        listings_by_district=[
            DistrictCount(district=district, count=count)
            for district, count in listing_district_counts.most_common(8)
        ],
        lead_count=len(leads),
        leads_by_source=dict(source_counts),
        leads_by_district=[
            DistrictCount(district=district, count=count)
            for district, count in lead_district_counts.most_common(8)
        ],
        leads_by_status={status: status_counts.get(status, 0) for status in LEAD_STATUSES},
        won_lead_count=status_counts.get("won", 0),
        active_follow_up_count=sum(1 for lead in leads if lead.auto_follow_up_enabled),
        scored_lead_count=len(scores),
        average_score=round(sum(scores) / len(scores), 1) if scores else None,
        score_distribution=[
            ScoreBucket(label=label, count=bucket_counts.get(label, 0)) for label in SCORE_BUCKET_ORDER
        ],
        conversion_rate=round(status_counts.get("won", 0) / len(leads) * 100, 1) if leads else None,
        closed_deal_count=len(closed_deals),
        total_deal_volume=total_deal_volume,
        total_revenue=total_revenue,
        average_commission=round(total_revenue / len(closed_deals), 2) if closed_deals else None,
        revenue_by_district=[
            DistrictRevenue(district=district, revenue=revenue)
            for district, revenue in revenue_by_district.most_common(8)
        ],
    )
