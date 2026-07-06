from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.middleware.tenant import get_tenant_db
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_my_profile(
    db: Session = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Profil sayfası için — hangi hesapla (e-posta) ve hangi rolle giriş
    yapıldığını gösterir. users RLS'li bir tablo olduğu için get_db değil
    get_tenant_db kullanılır (bkz. app/middleware/tenant.py)."""
    user = db.get(User, current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    return user
