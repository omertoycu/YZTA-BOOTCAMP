from fastapi import APIRouter, Depends, HTTPException
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
    """Şu an sadece notification_phone güncelleniyor — app rolünün offices
    üzerinde kolon seviyesinde sadece bu alan (ve subscription_plan) için
    UPDATE yetkisi var (bkz. migration 0015)."""
    office = db.get(Office, current_user["office_id"])
    if not office:
        raise HTTPException(status_code=404, detail="Ofis bulunamadı")
    office.notification_phone = payload.notification_phone
    db.commit()
    return office
