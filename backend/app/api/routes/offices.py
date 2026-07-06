from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.storage import MAX_PHOTO_BYTES, fetch_photo, upload_office_logo
from app.models.office import Office
from app.schemas.office import OfficeResponse, OfficeUpdate

router = APIRouter(prefix="/offices", tags=["offices"])


@router.get("/me", response_model=OfficeResponse)
def get_my_office(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    office = db.get(Office, current_user["office_id"])
    if not office:
        raise HTTPException(status_code=404, detail="Ofis bulunamadı")
    return office


@router.patch("/me", response_model=OfficeResponse)
def update_my_office(
    payload: OfficeUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """notification_phone ve whatsapp_phone_number_id güncellenebiliyor — app
    rolünün offices üzerinde kolon seviyesinde sadece bu ikisi (ve
    subscription_plan) için UPDATE yetkisi var (bkz. migration 0010/0015/0017).
    exclude_unset: frontend sadece TEK alanı güncellemek için PATCH atabiliyor,
    payload'da hiç yer almayan alan diğerini yanlışlıkla null'a düşürmemeli."""
    office = db.get(Office, current_user["office_id"])
    if not office:
        raise HTTPException(status_code=404, detail="Ofis bulunamadı")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(office, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Bu WhatsApp Phone Number ID başka bir ofis tarafından kullanılıyor"
        ) from exc
    return office


@router.post("/me/logo", response_model=OfficeResponse)
def upload_my_office_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Ofis logosu yükler — sidebar/profil/dashboard'da görünür ve markalı
    ulaşım raporu PDF'inde kullanılır (bkz. app/agents/location_report.py).
    İlan fotoğraflarıyla aynı S3 deposu/limitleri; app rolünün offices
    üzerinde logo_key için kolon seviyeli UPDATE yetkisi migration 0021'de."""
    office = db.get(Office, current_user["office_id"])
    if not office:
        raise HTTPException(status_code=404, detail="Ofis bulunamadı")

    file_bytes = file.file.read(MAX_PHOTO_BYTES + 1)
    if len(file_bytes) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Logo çok büyük (maksimum 8MB)")
    office.logo_key = upload_office_logo(file_bytes, file.content_type or "", str(office.id))
    db.commit()
    return office


@router.get("/logo/{key:path}")
def get_office_logo(key: str):
    """Logoyu private bucket'tan backend credential'ıyla akıtır (ilan
    fotoğraflarındaki GET /listings/photos/{key} ile aynı desen). Auth YOK —
    logo, ilan vitrini (/p/{id}) gibi login'siz sayfalarda da gösterilebilecek
    kamuya açık marka görseli; key'ler tahmin edilemez uuid içeriyor."""
    if not key.startswith("offices/"):
        raise HTTPException(status_code=404, detail="Logo bulunamadı")
    body, content_type = fetch_photo(key)
    return Response(
        content=body,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )
