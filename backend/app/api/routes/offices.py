from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
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
