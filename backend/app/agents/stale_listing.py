from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.pricing import suggest_price_range
from app.models.listing import Listing

# Bu eşiklerin altına düşen ilanlar sessizce atlanır — amaç danışmanı gürültüyle
# yormamak, sadece gerçekten "unutulmuş" ve "emsallere göre pahalı" portföyleri
# öne çıkarmak.
STALE_DAYS_THRESHOLD = 30
OVERPRICE_THRESHOLD = 0.05  # emsal üst sınırının %5 üzeri


def find_stale_listings(db: Session, now: datetime | None = None) -> list[dict]:
    """Pricing Agent'ın zaten hesapladığı emsal aralığını (bkz. app/agents/pricing.py)
    ilan yaşıyla birleştirip "uzun süredir aktif ve bölge emsallerine göre pahalı"
    portföyleri işaretler. Yeni bir dış API/maliyet gerektirmez — sadece mevcut
    k-NN emsal sorgusunu her aktif ilan için tekrar kullanır.

    RLS zaten sadece çağıran ofisin ilanlarını döndürür; burada office_id
    filtresi ayrıca uygulanmaz (bkz. list_listings route'undaki aynı desen).
    """
    now = now or datetime.now(timezone.utc)

    listings = db.execute(select(Listing).where(Listing.status == "active")).scalars().all()

    alerts = []
    for listing in listings:
        age_days = (now - listing.created_at).days
        if age_days < STALE_DAYS_THRESHOLD:
            continue

        suggestion = suggest_price_range(listing)
        if not suggestion["has_enough_data"]:
            continue

        suggested_max = suggestion["suggested_max"]
        price = float(listing.price)
        if price <= suggested_max * (1 + OVERPRICE_THRESHOLD):
            continue

        overprice_pct = round((price - suggested_max) / suggested_max * 100, 1)
        alerts.append(
            {
                "listing_id": listing.id,
                "title": listing.title,
                "district": listing.district,
                "price": price,
                "age_days": age_days,
                "suggested_max": suggested_max,
                "overprice_pct": overprice_pct,
                "message": (
                    f"Bu ilan {age_days} gündür aktif ve bölge emsallerine göre "
                    f"yaklaşık %{overprice_pct:g} pahalı — fiyat güncellemesi önerin."
                ),
            }
        )

    alerts.sort(key=lambda a: a["overprice_pct"], reverse=True)
    return alerts
