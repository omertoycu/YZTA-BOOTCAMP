from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.state import AgentState
from app.models.listing import Listing


def matching_node(state: AgentState, db: Session) -> AgentState:
    """Sprint 1 MVP: vektör benzerliği değil, basit SQL filtresi.

    Bütçe aralığı + oda sayısı + bölge eşleşmesiyle uygun portföyleri döner.
    Bölgesel emsal embedding tabanlı benzerlik Sprint 2'de Pricing Agent ile birlikte eklenecek.
    """
    query = select(Listing).where(Listing.status == "active")

    if state.get("district"):
        query = query.where(Listing.district == state["district"])
    if state.get("room_count"):
        query = query.where(Listing.room_count == state["room_count"])
    if state.get("budget_max") is not None:
        query = query.where(Listing.price <= state["budget_max"])
    if state.get("budget_min") is not None:
        query = query.where(Listing.price >= state["budget_min"])

    listings = db.execute(query).scalars().all()
    state["candidate_listings"] = [
        {
            "listing_id": str(listing.id),
            "title": listing.title,
            "price": float(listing.price),
            "match_reason": f"{listing.district} bölgesinde, bütçe ve oda sayısı kriterine uyuyor",
        }
        for listing in listings
    ]
    return state
