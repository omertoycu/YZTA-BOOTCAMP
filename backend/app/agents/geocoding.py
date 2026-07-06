import time
from math import asin, cos, radians, sin, sqrt

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.http import get_http_client
from app.models.geocoded_district import GeocodedDistrict

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
EARTH_RADIUS_KM = 6371.0

# Nominatim'in kullanım politikası saniyede 1 istekle sınırlı. Bir eşleştirme
# isteğinde birden çok bölge art arda (önbellekte olmayan) geocode edilirse,
# bu bekleme olmadan ikinci ve sonraki her istek 429/blok yiyip sessizce None
# dönüyordu — aranan bölgenin tam içindeki gerçek bir portföy bile sadece bu
# yüzden "eşleşme yok" sayılabiliyordu (gerçek prod hatası).
MIN_REQUEST_INTERVAL_SECONDS = 1.1
_last_request_at = 0.0


def _normalize(district: str) -> str:
    return district.strip().lower()


def geocode_district(db: Session, district: str) -> tuple[float, float] | None:
    """Bölge adını (latitude, longitude) çiftine çevirir, sonucu
    geocoded_districts'te önbelleğe alır. Ağ hatası veya sonuç bulunamazsa
    None döner — çağıran taraf bunu "yarıçap filtresi uygulanamadı" olarak
    yorumlayıp eski (bölge string eşleşmesi) davranışa dönmeli, asla sert
    hata fırlatmamalı."""
    if not district:
        return None
    normalized = _normalize(district)

    cached = db.execute(
        select(GeocodedDistrict).where(func.lower(GeocodedDistrict.district_name) == normalized)
    ).scalar_one_or_none()
    if cached:
        return float(cached.latitude), float(cached.longitude)

    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
        time.sleep(MIN_REQUEST_INTERVAL_SECONDS - elapsed)
    _last_request_at = time.monotonic()

    try:
        with get_http_client() as client:
            response = client.get(
                NOMINATIM_URL,
                params={"q": f"{district}, Türkiye", "format": "json", "limit": 1},
            )
            response.raise_for_status()
            results = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    if not results:
        return None

    try:
        latitude = float(results[0]["lat"])
        longitude = float(results[0]["lon"])
    except (KeyError, ValueError, TypeError):
        return None

    db.add(GeocodedDistrict(district_name=normalized, latitude=latitude, longitude=longitude))
    try:
        db.commit()
    except IntegrityError:
        # Eşzamanlı iki istek aynı bölgeyi aynı anda geocode etmiş olabilir;
        # koordinat zaten elimizde olduğu için sorun değil.
        db.rollback()
    return latitude, longitude


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_r, lon1_r, lat2_r, lon2_r = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))
