import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.agents.appointment_reminder import run_due_appointment_reminders
from app.agents.follow_up import run_due_follow_ups
from app.core.config import settings
from app.core.db import get_db

router = APIRouter(prefix="/internal", tags=["internal"])


def _verify_cron_secret(x_cron_secret: str | None) -> None:
    if not settings.cron_secret:
        raise HTTPException(status_code=503, detail="Zamanlanmış görevler şu an aktif değil")
    if not x_cron_secret or not hmac.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status_code=401, detail="Geçersiz cron secret")


@router.post("/run-follow-ups")
def run_follow_ups(
    db: Session = Depends(get_db),
    x_cron_secret: str | None = Header(default=None),
):
    """Vadesi gelen otomatik WhatsApp takip mesajlarını gönderir. Bir cron
    tarafından tetiklenmek için tasarlandı (Railway cron / GitHub Actions
    schedule / harici uptime servisi) — JWT yerine paylaşılan CRON_SECRET
    header'ıyla korunur, çünkü çağıran bir kullanıcı değil, altyapı.

    Cron aralığı önerisi: saatte bir. Zincir aşamaları gün mertebesinde olduğu
    için daha sık çalıştırmanın faydası yok; başarısız gönderimler bir sonraki
    çalışmada yeniden denenir (bkz. app/agents/follow_up.py).
    """
    _verify_cron_secret(x_cron_secret)
    return run_due_follow_ups(db)


@router.post("/run-appointment-reminders")
def run_appointment_reminders(
    db: Session = Depends(get_db),
    x_cron_secret: str | None = Header(default=None),
):
    """Randevusuna 24 saatten az kalan adaylara tek seferlik bir WhatsApp
    hatırlatması gönderir (bkz. app/agents/appointment_reminder.py). Bilinçli
    olarak /run-follow-ups'tan AYRI bir endpoint — mevcut response şeklini
    (testlerin ve cron izlemenin bağımlı olduğu düz `{"sent": ..., "failed": ...}`)
    bozmadan eklenebilsin diye. Cron her ikisini de saatte bir çağırmalı."""
    _verify_cron_secret(x_cron_secret)
    return run_due_appointment_reminders(db)
