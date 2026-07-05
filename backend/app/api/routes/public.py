from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_public_db
from app.models.listing import Listing
from app.models.listing_view import ListingView
from app.models.office import Office
from app.schemas.public import PublicListingResponse

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/listings/{listing_id}", response_model=PublicListingResponse)
def get_public_listing(listing_id: str, db: Session = Depends(get_public_db)):
    """Login gerektirmeyen ilan vitrini sayfası — danışmanın adaya WhatsApp'tan
    attığı markalı mikro-link (/p/{id}). portfoyai_public rolüyle bağlanır (bkz.
    migration 0013): bu rol için listings tablosunda office_id'den bağımsız ayrı
    bir SELECT policy'si var, normal tenant context'e (SET LOCAL) hiç gerek yok.
    Her ziyaret listing_views'e bir satır ekler (Scoring/Reports için sinyal)."""
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Portföy bulunamadı")

    office = db.get(Office, listing.office_id)

    db.add(ListingView(office_id=listing.office_id, listing_id=listing.id))
    db.commit()

    return PublicListingResponse(
        id=listing.id,
        title=listing.title,
        district=listing.district,
        price=float(listing.price),
        room_count=listing.room_count,
        square_meters=listing.square_meters,
        photos=listing.photos,
        office_name=office.name if office else "PortföyAI",
    )
