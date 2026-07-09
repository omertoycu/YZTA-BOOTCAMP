from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.geo import search_cities, search_districts, search_neighborhoods

router = APIRouter(prefix="/geo", tags=["geo"])

# İlan formundaki şehir→ilçe→mahalle otomatik tamamlama için statik sözlük
# aramaları (bkz. app/core/geo.py). DB'ye dokunmaz; auth yine de zorunlu —
# panel dışından anonim taramaya açık bir yüzey bırakmamak için.


@router.get("/cities", response_model=list[str])
def list_cities(
    q: str = Query("", max_length=120),
    current_user: dict = Depends(get_current_user),
):
    return search_cities(q)


@router.get("/districts", response_model=list[str])
def list_districts(
    q: str = Query("", max_length=120),
    city: str | None = Query(None, max_length=120),
    current_user: dict = Depends(get_current_user),
):
    return search_districts(q, city=city)


@router.get("/neighborhoods", response_model=list[str])
def list_neighborhoods(
    q: str = Query("", max_length=120),
    city: str | None = Query(None, max_length=120),
    district: str | None = Query(None, max_length=120),
    current_user: dict = Depends(get_current_user),
):
    return search_neighborhoods(q, city=city, district=district)
