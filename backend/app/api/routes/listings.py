from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.listing_import import (
    ListingFetchError,
    UnsupportedListingSiteError,
    extract_listing,
    parse_listing_html,
)
from app.agents.location_report import LocationReportError, get_travel_summary, render_report_pdf
from app.agents.pricing import index_listing, remove_listing_from_index, suggest_price_range
from app.agents.stale_listing import find_stale_listings
from app.agents.voice_listing import MAX_AUDIO_BYTES, VoiceListingError, transcribe_and_extract
from app.api.deps import get_current_user
from app.core.storage import MAX_PHOTO_BYTES, fetch_photo, upload_photo
from app.middleware.tenant import get_tenant_db
from app.models.listing import Listing
from app.models.listing_view import ListingView
from app.models.office import Office
from app.schemas.listing import (
    ListingCreate,
    ListingExtractFromHtmlRequest,
    ListingExtractRequest,
    ListingExtractResponse,
    ListingResponse,
    ListingStatusUpdate,
    LocationReportRequest,
    VoiceListingDraftResponse,
)
from app.schemas.pricing import PricingSuggestionResponse, StaleListingAlert
from app.schemas.public import ListingViewStatsResponse

router = APIRouter(prefix="/listings", tags=["listings"])

# active: eşleştirmeye girer; optioned (kapora/opsiyon alındı) ve sold girmez —
# Matching Agent sadece status == "active" portföyleri tarar (bkz. matching.py).
LISTING_STATUSES = ("active", "optioned", "sold")


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
    """Portallar sunucudan atılan istekleri (bot koruması) engellediği için
    danışman sayfa kaynağını kendi tarayıcısından kopyalayıp buraya yapıştırır —
    fetch adımı yok. Kaynağın Sahibinden mi Emlakjet mi olduğu otomatik tespit
    edilir (bkz. app/agents/listing_import.py: detect_source)."""
    fields = parse_listing_html(payload.html)
    return ListingExtractResponse(**fields)


@router.post("/voice-draft", response_model=VoiceListingDraftResponse)
def create_voice_draft(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),  # auth zorunlu, açık proxy istismarını önler
):
    """Danışmanın kaydettiği/yüklediği sesli notu Gemini ile transkript edip
    yapılandırılmış bir ilan taslağına çevirir. Hiçbir şey otomatik yayınlanmaz —
    frontend, danışman taslağı gözden geçirip onayladıktan sonra normal
    POST /listings akışıyla ilanı oluşturur."""
    audio_bytes = file.file.read(MAX_AUDIO_BYTES + 1)
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Ses kaydı çok büyük (maksimum 20MB)")
    if not audio_bytes:
        raise HTTPException(status_code=422, detail="Boş ses kaydı")

    content_type = (file.content_type or "audio/webm").split(";")[0].strip()

    try:
        draft = transcribe_and_extract(audio_bytes, content_type)
    except VoiceListingError as exc:
        if str(exc) == "__not_configured__":
            raise HTTPException(status_code=503, detail="Sesli not işleme şu an aktif değil") from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return VoiceListingDraftResponse(**draft)


@router.patch("/{listing_id}/status", response_model=ListingResponse)
def update_listing_status(
    listing_id: str,
    payload: ListingStatusUpdate,
    db: Session = Depends(get_tenant_db),
):
    """Portföyün durumunu değiştirir. Satıldı/opsiyonlu portföyler silinmez —
    Pricing Agent'ın emsal verisi ve ofis raporları için tarihçe olarak kalır,
    sadece eşleştirmeden çıkar."""
    if payload.status not in LISTING_STATUSES:
        raise HTTPException(
            status_code=400, detail=f"Geçersiz durum. Geçerli değerler: {', '.join(LISTING_STATUSES)}"
        )
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Portföy bulunamadı")
    listing.status = payload.status
    db.commit()
    return listing


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
    key = upload_photo(file_bytes, file.content_type or "", listing_id)
    listing.photos = [*listing.photos, key]
    db.commit()
    return listing


@router.get("/photos/{key:path}")
def get_listing_photo(key: str):
    """Railway Buckets (Tigris) public bucket erişimini desteklemiyor; fotoğraflar
    bu route üzerinden backend credential'ıyla bucket'tan çekilip tarayıcıya akıtılır.
    ListingResponse.photos alanı zaten bu route'a işaret eden URL'leri döner
    (bkz. app/schemas/listing.py, app/core/storage.py: photo_proxy_url)."""
    body, content_type = fetch_photo(key)
    return Response(
        content=body,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.post("/{listing_id}/location-report")
def create_location_report(
    listing_id: str,
    payload: LocationReportRequest,
    db: Session = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Markalı ulaşım/konum raporu PDF'i üretir. Portföyün bölgesi origin,
    danışmanın girdiği hedef adres destination olarak Google Directions API'ye
    serbest metin gönderilir — Google kendi içinde geocode ettiği için ayrıca
    Nominatim'e gerek yok. PDF diske/S3'e kaydedilmez, doğrudan indirilir."""
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Portföy bulunamadı")
    office = db.get(Office, current_user["office_id"])

    origin = f"{listing.district}, İstanbul"
    try:
        travel_summary = get_travel_summary(origin, payload.target_address)
    except LocationReportError as exc:
        if str(exc) == "__not_configured__":
            raise HTTPException(status_code=503, detail="Ulaşım raporu şu an aktif değil") from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    pdf_bytes = render_report_pdf(
        office_name=office.name if office else "PortföyAI",
        listing_title=listing.title,
        listing_district=listing.district,
        target_label=payload.target_label or payload.target_address,
        travel_summary=travel_summary,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="ulasim-raporu-{listing_id}.pdf"'},
    )


@router.get("/stale-alerts", response_model=list[StaleListingAlert])
def get_stale_listing_alerts(db: Session = Depends(get_tenant_db)):
    """30+ gündür aktif ve Pricing Agent'ın emsal aralığına göre pahalı kalan
    portföyleri işaretler (bkz. app/agents/stale_listing.py) — danışmanı fiyat
    güncellemesi için dürten, sıfır ek maliyetli bir proaktif uyarı. Statik yol
    olduğu için /{listing_id}'den ÖNCE tanımlanmalı, yoksa FastAPI "stale-alerts"
    değerini listing_id olarak yakalar."""
    return find_stale_listings(db)


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


@router.delete("/{listing_id}", status_code=204)
def delete_listing(listing_id: str, db: Session = Depends(get_tenant_db)):
    """Portföyü kalıcı olarak siler. Bağlı görüntülenme kayıtları
    (listing_views) migration 0019'daki ON DELETE CASCADE ile otomatik
    silinir. Postgres kaynak-of-truth: önce oradan silinip commit edilir,
    ChromaDB'deki emsal embedding'i sonra best-effort temizlenir — Chroma
    hatası DB silmeyi asla engellemez (S3'teki fotoğraflar bilinçli olarak
    silinmez, bkz. plan notu). Geri alınamaz, frontend onay ister."""
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Portföy bulunamadı")
    db.delete(listing)
    db.commit()
    try:
        remove_listing_from_index(listing_id)
    except Exception:
        pass


@router.get("/{listing_id}/pricing-suggestion", response_model=PricingSuggestionResponse)
def get_pricing_suggestion(listing_id: str, db: Session = Depends(get_tenant_db)):
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Portföy bulunamadı")
    return suggest_price_range(listing)


@router.get("/{listing_id}/view-stats", response_model=ListingViewStatsResponse)
def get_listing_view_stats(listing_id: str, db: Session = Depends(get_tenant_db)):
    """İlan vitrini (/public/listings/{id}) kaç kez görüntülendi — danışman
    panelinde "Vitrin İstatistikleri" olarak gösterilir. Görüntülenme kayıtları
    portfoyai_public rolüyle atıldığı için (bkz. migration 0013) burada normal
    tenant-scoped SELECT policy'siyle (portfoyai_app) okunur."""
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Portföy bulunamadı")

    view_count, last_viewed_at = db.execute(
        select(func.count(ListingView.id), func.max(ListingView.viewed_at)).where(
            ListingView.listing_id == listing.id
        )
    ).one()
    return ListingViewStatsResponse(view_count=view_count, last_viewed_at=last_viewed_at)
