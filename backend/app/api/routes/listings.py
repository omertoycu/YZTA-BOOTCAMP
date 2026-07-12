from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.listing_import import (
    ListingFetchError,
    UnsupportedListingSiteError,
    extract_listing,
    parse_listing_html,
    parse_sahibinden_portfolio,
)
from app.agents.market_price_check import fetch_market_price_check
from app.agents.pricing import (
    index_listing,
    reindex_office_listings,
    remove_listing_from_index,
    suggest_price_range,
)
from app.agents.stale_listing import find_stale_listings
from app.agents.store_import import (
    StoreImportError,
    UnsupportedStoreUrlError,
    import_store_listings,
)
from app.agents.voice_listing import MAX_AUDIO_BYTES, VoiceListingError, transcribe_and_extract
from app.api.deps import get_current_user
from app.core.geo import infer_city
from app.core.http import get_http_client
from app.core.storage import MAX_PHOTO_BYTES, delete_photo, fetch_photo, upload_photo
from app.middleware.tenant import get_tenant_db
from app.models.listing import Listing
from app.models.listing_view import ListingView
from app.schemas.listing import (
    ListingCreate,
    ListingExtractFromHtmlRequest,
    ListingExtractRequest,
    ListingExtractResponse,
    ListingPhotoFromUrlRequest,
    ListingPortfolioExtractResponse,
    ListingPropertyTypeUpdate,
    ListingResponse,
    ListingStatusUpdate,
    ListingTypeUpdate,
    ListingUpdate,
    StoreImportRequest,
    VoiceListingDraftResponse,
)
from app.schemas.pricing import MarketPriceCheckResponse, PricingSuggestionResponse, StaleListingAlert
from app.schemas.public import ListingViewStatsResponse

router = APIRouter(prefix="/listings", tags=["listings"])

# active: eşleştirmeye girer; optioned (kapora/opsiyon alındı) ve sold girmez —
# Matching Agent sadece status == "active" portföyleri tarar (bkz. matching.py).
LISTING_STATUSES = ("active", "optioned", "sold")

# Toplu aktarımda kart görselini indirmek için izin verilen host'lar — sadece
# Sahibinden'in kendi görsel CDN'i (bkz. listing_import.py'de çıkarılan
# cover_photo_url). Bu bir SSRF önlemi: rastgele bir URL'i sunucudan
# indirtmeye izin vermek, danışman panelinden dahili servislere istek
# attırmak için istismar edilebilirdi.
ALLOWED_PHOTO_URL_HOSTS = ("shbdn.com",)


@router.post("", response_model=ListingResponse, status_code=201)
def create_listing(
    payload: ListingCreate,
    db: Session = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    data = payload.model_dump()
    # Portal aktarımı/sesli not şehir bilgisi vermeden gelebilir — ilçe
    # (+mahalle) statik sözlükte tekil eşleşiyorsa şehir etiketi otomatik konur.
    if not data.get("city") and data.get("district"):
        data["city"] = infer_city(data["district"], data.get("neighborhood"))
    listing = Listing(
        office_id=current_user["office_id"],
        agent_id=current_user["user_id"],
        **data,
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


@router.post("/extract-portfolio-from-html", response_model=ListingPortfolioExtractResponse)
def extract_portfolio_from_html(
    payload: ListingExtractFromHtmlRequest,
    current_user: dict = Depends(get_current_user),  # auth zorunlu, açık proxy istismarını önler
):
    """Danışmanın Sahibinden'deki KENDİ portföyünün listelendiği sayfadan
    (view-source ile kopyalanan kaynak) TÜM ilanları tek seferde ayrıştırır —
    tek ilan sayfasından (extract-from-html) farklı bir HTML yapısı kullanır,
    bu yüzden ayrı endpoint (bkz. listing_import.parse_sahibinden_portfolio).
    Fetch adımı yok, sadece yapıştırılan metin ayrıştırılır; hiçbir portföy
    otomatik oluşturulmaz, danışman ayrıştırılan listeyi gözden geçirip
    seçtiklerini onaylar."""
    listings = parse_sahibinden_portfolio(payload.html)
    return ListingPortfolioExtractResponse(listings=[ListingExtractResponse(**item) for item in listings])


@router.post("/import-store", response_model=ListingPortfolioExtractResponse)
def import_from_store(
    payload: StoreImportRequest,
    current_user: dict = Depends(get_current_user),  # auth zorunlu, açık proxy istismarını önler
):
    """Sahibinden mağaza URL'sinden (örn. toycuemlak.sahibinden.com) tüm
    ilanları Apify üzerinden çekip ayrıştırır — "kaynak yapıştır" toplu
    aktarımının (extract-portfolio-from-html) fetch adımı otomatikleşmiş hali,
    inceleme/onay akışı birebir aynı: hiçbir ilan otomatik oluşturulmaz,
    danışman inceleme kartlarından onayladıklarını normal POST /listings ile
    kaydeder (Postgres + ChromaDB emsal endeksi oraya bağlı). Senkron çalışır
    (Apify 30-90 sn sürebilir, frontend yükleniyor durumu gösterir) — job/
    polling altyapısı bilinçli olarak kurulmadı, taslak listesi tek yanıtta
    döner (bkz. app/agents/store_import.py)."""
    try:
        listings = import_store_listings(payload.url)
    except UnsupportedStoreUrlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StoreImportError as exc:
        if str(exc) == "__not_configured__":
            raise HTTPException(status_code=503, detail="Mağaza aktarımı şu an aktif değil") from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ListingPortfolioExtractResponse(listings=[ListingExtractResponse(**item) for item in listings])


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


@router.patch("/{listing_id}", response_model=ListingResponse)
def update_listing(
    listing_id: str,
    payload: ListingUpdate,
    db: Session = Depends(get_tenant_db),
):
    """Danışmanın portföy detay sayfasından başlık/fiyat/konum/oda/m² gibi temel
    alanları düzeltebilmesi için genel amaçlı kısmi güncelleme. status/listing_type/
    property_type için ayrı, dar kapsamlı route'lar zaten var (yukarıda) — onlara
    dokunulmaz. Fiyat veya konum değişebildiği için ChromaDB emsal endeksi
    (Pricing Agent) yeniden yazılır, aksi halde eski değerlerle arar."""
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Portföy bulunamadı")

    updates = payload.model_dump(exclude_unset=True)
    if "title" in updates and not updates["title"].strip():
        raise HTTPException(status_code=422, detail="Başlık boş olamaz")
    if "district" in updates and not updates["district"].strip():
        raise HTTPException(status_code=422, detail="İlçe boş olamaz")
    if "room_count" in updates and not updates["room_count"].strip():
        raise HTTPException(status_code=422, detail="Oda sayısı boş olamaz")
    if "price" in updates and updates["price"] <= 0:
        raise HTTPException(status_code=422, detail="Fiyat sıfırdan büyük olmalı")

    for field, value in updates.items():
        setattr(listing, field, value)

    # city gönderilmeden sadece district/neighborhood güncellenmiş olabilir —
    # create_listing ile aynı çıkarım mantığı (bkz. app/core/geo.py: infer_city).
    if not listing.city and listing.district:
        listing.city = infer_city(listing.district, listing.neighborhood)

    db.commit()
    index_listing(listing)
    return listing


@router.delete("/{listing_id}/photos/{photo_index}", response_model=ListingResponse)
def delete_listing_photo(
    listing_id: str,
    photo_index: int,
    db: Session = Depends(get_tenant_db),
):
    """Fotoğraf listesinden tek bir fotoğrafı kaldırır (sıra numarasına göre —
    ListingResponse.photos'un döndürdüğü proxy URL'lerinden değil, ham S3
    key'inden bağımsız olsun diye index kullanılıyor). S3'ten silme best-effort
    (bkz. storage.delete_photo); listing.photos'tan çıkarma her koşulda olur."""
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Portföy bulunamadı")
    photos = list(listing.photos)
    if photo_index < 0 or photo_index >= len(photos):
        raise HTTPException(status_code=404, detail="Fotoğraf bulunamadı")

    key = photos.pop(photo_index)
    listing.photos = photos
    db.commit()
    delete_photo(key)
    return listing


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


@router.patch("/{listing_id}/type", response_model=ListingResponse)
def update_listing_type(
    listing_id: str,
    payload: ListingTypeUpdate,
    db: Session = Depends(get_tenant_db),
):
    """Migration 0020 mevcut tüm portföyleri varsayılan "sale" işaretledi —
    gerçekte kiralık olanları danışmanın panelden düzeltebilmesi gerekiyor
    (aksi halde emsal havuzu yanlış tipte kalır). Değişiklik sonrası ilan
    ChromaDB'de de güncellenir ki fiyat önerisi doğru havuza baksın."""
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Portföy bulunamadı")
    listing.listing_type = payload.listing_type
    db.commit()
    index_listing(listing)
    return listing


@router.patch("/{listing_id}/property-type", response_model=ListingResponse)
def update_listing_property_type(
    listing_id: str,
    payload: ListingPropertyTypeUpdate,
    db: Session = Depends(get_tenant_db),
):
    """Konut/iş yeri/arsa ayrımı danışman panelinden düzeltilebilir — Matching
    Agent bunu bilmeden ticari/arsa ilanlarına anlamsız oda sayısı filtresi
    uygulamaya devam eder (bkz. app/agents/matching.py)."""
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Portföy bulunamadı")
    listing.property_type = payload.property_type
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


@router.post("/{listing_id}/photos/from-url", response_model=ListingResponse)
def upload_listing_photo_from_url(
    listing_id: str,
    payload: ListingPhotoFromUrlRequest,
    db: Session = Depends(get_tenant_db),
):
    """Sahibinden'den toplu aktarımda kart görselini (cover_photo_url) danışman
    adına indirip kendi depolamamıza yükler — danışman en azından hangi evin
    hangisi olduğunu hatırlayabilsin. Tarayıcıdan doğrudan çapraz-origin fetch
    genelde CORS'a takıldığı için indirme sunucu tarafında yapılıyor. Sadece
    Sahibinden'in kendi görsel CDN'ine (ALLOWED_PHOTO_URL_HOSTS) izin verilir —
    aksi halde bu route SSRF için istismar edilebilirdi. Best-effort: bu
    endpoint başarısız olursa ilan zaten oluşturulmuş olur, danışman fotoğrafı
    panelden elle ekleyebilir."""
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Portföy bulunamadı")

    host = urlparse(payload.url).hostname or ""
    if not any(host == allowed or host.endswith(f".{allowed}") for allowed in ALLOWED_PHOTO_URL_HOSTS):
        raise HTTPException(status_code=400, detail="Desteklenmeyen görsel kaynağı")

    try:
        with get_http_client() as client:
            response = client.get(payload.url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Fotoğraf indirilemedi") from exc

    file_bytes = response.content
    if len(file_bytes) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Fotoğraf çok büyük (maksimum 8MB)")
    content_type = response.headers.get("content-type", "").split(";")[0].strip()
    key = upload_photo(file_bytes, content_type, listing_id)
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
    # ChromaDB her deploy'da sıfırlandığı için (kalıcı Volume yok) sorgudan
    # önce ofisin ilanları endekse geri yazılır — bkz. reindex_office_listings.
    reindex_office_listings(db)
    return suggest_price_range(listing)


@router.get("/{listing_id}/market-price-check", response_model=MarketPriceCheckResponse)
def get_market_price_check(listing_id: str, db: Session = Depends(get_tenant_db)):
    """Ofisin kendi portföyüyle sınırlı yukarıdaki öneriden farklı olarak,
    Gemini'nin web arama (grounding) aracıyla piyasa genelinde muadil ilanları
    araştırıp bir aralık üretir (bkz. app/agents/market_price_check.py).
    fetch_market_price_check tamamen best-effort olduğu için (hiç exception
    fırlatmaz) burada ayrıca 503 map'lemeye gerek yok — has_market_data=False
    zaten "veri yok" anlamına geliyor, hata değil."""
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Portföy bulunamadı")
    return fetch_market_price_check(listing)


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
