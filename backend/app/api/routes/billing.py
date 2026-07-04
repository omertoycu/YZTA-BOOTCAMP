from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.db import get_db
from app.core.payments import IyzicoError, initialize_checkout_form, retrieve_checkout_result
from app.middleware.tenant import get_tenant_db
from app.models.office import Office
from app.models.user import User
from app.schemas.billing import CheckoutRequest, CheckoutResponse, PlanInfo

router = APIRouter(prefix="/billing", tags=["billing"])

# 3 pricingPlan (bkz. README "İş Modeli Notu"). Fiyatlar aylık TL; iyzico'ya
# string olarak gider (ondalık hassasiyet kaybı olmasın diye).
PLANS: dict[str, dict] = {
    "starter": {
        "name": "Starter",
        "monthly_price": "0",
        "features": ["5 aktif portföy", "Temel eşleştirme", "Tek danışman"],
    },
    "pro": {
        "name": "Pro",
        "monthly_price": "990",
        "features": [
            "Sınırsız portföy",
            "Sesli Not → İlan",
            "Ulaşım/Konum Raporu (PDF)",
            "Otomatik WhatsApp takip zinciri",
        ],
    },
    "office": {
        "name": "Ofis",
        "monthly_price": "1990",
        "features": [
            "Pro'daki her şey",
            "5 danışmana kadar",
            "Fiyat önerisi (emsal analizi)",
            "Öncelikli destek",
        ],
    },
}


@router.get("/plans", response_model=list[PlanInfo])
def list_plans(
    db: Session = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    office = db.get(Office, current_user["office_id"])
    current_plan = office.subscription_plan if office else "starter"
    return [
        PlanInfo(
            id=plan_id,
            name=plan["name"],
            monthly_price=float(plan["monthly_price"]),
            features=plan["features"],
            is_current=plan_id == current_plan,
        )
        for plan_id, plan in PLANS.items()
    ]


@router.post("/checkout", response_model=CheckoutResponse)
def start_checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """iyzico Checkout Form başlatır, danışmanın yönlendirileceği ödeme sayfası
    URL'ini döner. Ödeme iyzico'nun sayfasında tamamlanır; sonuç callback'e düşer."""
    plan = PLANS.get(payload.plan)
    if plan is None:
        raise HTTPException(status_code=400, detail="Geçersiz plan")
    if plan["monthly_price"] == "0":
        raise HTTPException(status_code=400, detail="Ücretsiz plan için ödeme gerekmez")

    office = db.get(Office, current_user["office_id"])
    user = db.get(User, current_user["user_id"])
    if office is None or user is None:
        raise HTTPException(status_code=404, detail="Ofis bulunamadı")
    if office.subscription_plan == payload.plan:
        raise HTTPException(status_code=400, detail="Bu plana zaten abonesiniz")

    try:
        result = initialize_checkout_form(
            office_id=str(office.id),
            plan_id=payload.plan,
            plan_name=plan["name"],
            monthly_price=plan["monthly_price"],
            buyer_email=user.email,
            buyer_name=office.name,
            callback_url=f"{settings.public_base_url}/billing/callback",
        )
    except IyzicoError as exc:
        if str(exc) == "__not_configured__":
            raise HTTPException(status_code=503, detail="Ödeme altyapısı şu an aktif değil") from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return CheckoutResponse(payment_page_url=result["payment_page_url"])


@router.post("/callback")
def checkout_callback(token: str = Form(...), db: Session = Depends(get_db)):
    """iyzico, ödeme sayfası tamamlanınca kullanıcının tarayıcısını buraya form
    POST ile yönlendirir. Token istemciden gelir ama ödeme sonucuna asla
    istemci beyanıyla karar verilmez — sonuç her zaman iyzico API'sinden
    doğrulanır (bkz. app/core/payments.py). Bu yüzden JWT auth yok: endpoint'i
    çağırabilen herkes sadece iyzico'nun zaten onayladığı bir ödemeyi işletebilir.

    Yanıt bir tarayıcı yönlendirmesi olduğu için hata durumları JSON değil,
    frontend'in /billing?status=... sayfasına redirect olarak döner.
    """
    try:
        result = retrieve_checkout_result(token)
    except IyzicoError:
        return RedirectResponse(f"{settings.frontend_base_url}/billing?status=error", status_code=303)

    if not result["paid"] or not result["office_id"] or result["plan_id"] not in PLANS:
        return RedirectResponse(f"{settings.frontend_base_url}/billing?status=failed", status_code=303)

    # offices RLS'siz/global; app rolünün UPDATE yetkisi kolon seviyesinde sadece
    # subscription_plan'a açık (bkz. migration 0010). office_id iyzico'nun
    # doğruladığı conversationId'den geliyor.
    db.execute(
        update(Office)
        .where(Office.id == result["office_id"])
        .values(subscription_plan=result["plan_id"])
    )
    db.commit()

    return RedirectResponse(f"{settings.frontend_base_url}/billing?status=success", status_code=303)
