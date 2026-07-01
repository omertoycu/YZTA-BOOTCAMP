from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.middleware.tenant import get_tenant_db
from app.models.listing import Listing
from app.schemas.listing import ListingCreate, ListingResponse

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
    return listing


@router.get("", response_model=list[ListingResponse])
def list_listings(db: Session = Depends(get_tenant_db)):
    # RLS, current_user'ın office_id'si dışındaki satırları zaten filtreler;
    # burada office_id ile ayrıca filtrelemeye gerek yok.
    return db.execute(select(Listing)).scalars().all()
