from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.pricing import index_listing, suggest_price_range
from app.api.deps import get_current_user
from app.middleware.tenant import get_tenant_db
from app.models.listing import Listing
from app.schemas.listing import ListingCreate, ListingResponse
from app.schemas.pricing import PricingSuggestionResponse

router = APIRouter(prefix="/listings", tags=["listings"])


@router.post("", response_model=ListingResponse, status_code=201)
def create_listing(
    payload: ListingCreate,
    db: Session = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    listing = Listing(
        office_id=current_user["office_id"],
        agent_id=current_user["user_id"],
        **payload.model_dump(),
    )
    db.add(listing)
    db.commit()
    index_listing(listing)
    return listing


@router.get("", response_model=list[ListingResponse])
def list_listings(db: Session = Depends(get_tenant_db)):
    # RLS, current_user'ın office_id'si dışındaki satırları zaten filtreler;
    # burada office_id ile ayrıca filtrelemeye gerek yok.
    return db.execute(select(Listing)).scalars().all()


@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing(listing_id: str, db: Session = Depends(get_tenant_db)):
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Portföy bulunamadı")
    return listing


@router.get("/{listing_id}/pricing-suggestion", response_model=PricingSuggestionResponse)
def get_pricing_suggestion(listing_id: str, db: Session = Depends(get_tenant_db)):
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Portföy bulunamadı")
    return suggest_price_range(listing)
