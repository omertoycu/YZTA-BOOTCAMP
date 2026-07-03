from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.geocoding import geocode_district, haversine_km
from app.agents.state import AgentState
from app.models.listing import Listing


def matching_node(state: AgentState, db: Session) -> AgentState:
    """Sprint 1 MVP: vektör benzerliği değil, basit SQL filtresi.

    Bütçe aralığı + oda sayısı + bölge eşleşmesiyle uygun portföyleri döner.
    `radius_km` set edilmişse ve lead'in bölgesi geocode edilebiliyorsa, tam
    bölge string eşleşmesi yerine coğrafi yarıçap filtresi uygulanır (bkz.
    app/agents/geocoding.py) — geocode başarısız olursa (ağ hatası, bilinmeyen
    bölge) sessizce eski davranışa (bölge string eşleşmesi) düşülür.
    Bölgesel emsal embedding tabanlı benzerlik Sprint 2'de Pricing Agent ile birlikte eklendi.
    """
    radius_km = state.get("radius_km")
    center = geocode_district(db, state["district"]) if radius_km and state.get("district") else None

    query = select(Listing).where(Listing.status == "active")
    if not center and state.get("district"):
        query = query.where(Listing.district == state["district"])
    if state.get("room_count"):
        query = query.where(Listing.room_count == state["room_count"])
    if state.get("budget_max") is not None:
        query = query.where(Listing.price <= state["budget_max"])
    if state.get("budget_min") is not None:
        query = query.where(Listing.price >= state["budget_min"])

    listings = db.execute(query).scalars().all()

    candidates = []
    for listing in listings:
        if center:
            listing_coords = geocode_district(db, listing.district)
            if listing_coords is None:
                continue
            distance = haversine_km(*center, *listing_coords)
            if distance > radius_km:
                continue
            reason = f"{listing.district} bölgesi, aradığınız konuma ~{distance:.1f} km mesafede"
        else:
            reason = f"{listing.district} bölgesinde, bütçe ve oda sayısı kriterine uyuyor"

        candidates.append(
            {
                "listing_id": str(listing.id),
                "title": listing.title,
                "price": float(listing.price),
                "match_reason": reason,
            }
        )

    state["candidate_listings"] = candidates
    return state
