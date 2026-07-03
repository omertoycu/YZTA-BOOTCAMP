from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.listing_import import (
    ListingFetchError,
    UnsupportedListingSiteError,
    extract_listing,
    parse_sahibinden,
)
from app.agents.pricing import index_listing, suggest_price_range
from app.api.deps import get_current_user
from app.core.storage import MAX_PHOTO_BYTES, upload_photo
from app.middleware.tenant import get_tenant_db
from app.models.listing import Listing
from app.schemas.listing import (
    ListingCreate,
    ListingExtractFromHtmlRequest,
    ListingExtractRequest,
    ListingExtractResponse,
    ListingResponse,
)
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


@router.post("/extract-from-url", response_model=ListingExtractResponse)
def extract_from_url(
    payload: ListingExtractRequest,
    current_user: dict = Depends(get_current_user),  # auth zorunlu, açık proxy istismarını önler
):
    try:
        fields = extract_listing(payload.url)
    except UnsupportedListingSiteError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ListingFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ListingExtractResponse(**fields)


@router.post("/extract-from-html", response_model=ListingExtractResponse)
def extract_from_html(
    payload: ListingExtractFromHtmlRequest,
    current_user: dict = Depends(get_current_user),  # auth zorunlu, açık proxy istismarını önler
):
    """Sahibinden sunucudan atılan istekleri (bot koruması) engellediği için
    danışman sayfa kaynağını kendi tarayıcısından kopyalayıp buraya yapıştırır —
    fetch adımı yok, sadece parse_sahibinden ile ayrıştırma."""
    fields = parse_sahibinden(payload.html)
    return ListingExtractResponse(**fields)


@router.post("/{listing_id}/photos", response_model=ListingResponse)
def upload_listing_photo(
    listing_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_tenant_db),
):
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Portföy bulunamadı")

    file_bytes = file.file.read(MAX_PHOTO_BYTES + 1)
    if len(file_bytes) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Fotoğraf çok büyük (maksimum 8MB)")
    url = upload_photo(file_bytes, file.content_type or "", listing_id)
    listing.photos = [*listing.photos, url]
    db.commit()
    return listing


@router.get("", response_model=list[ListingResponse])
def list_listings(db: Session = Depends(get_tenant_db)):
    # RLS, current_user'ın office_id'si dışındaki satırları zaten filtreler;
    # burada office_id ile ayrıca filtrelemeye gerek yok.
    query = select(Listing).order_by(Listing.created_at.desc())
    return db.execute(query).scalars().all()


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
