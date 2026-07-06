import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.geocoding import geocode_district, haversine_km
from app.agents.state import AgentState
from app.models.listing import Listing

# Bütçenin biraz üzerinde/altında kalan ama aksi halde tam uyan bir portföyü
# tamamen elemek yerine "yakın eşleşme" olarak sunmak için tolerans payı —
# katı ≤/≥ filtresi ₺1 farkla bile gerçek uygun bir evi listeden düşürüyordu.
BUDGET_TOLERANCE_RATIO = 0.05

_ROOM_SEPARATOR = re.compile(r"\s*\+\s*")


def _normalize(value: str) -> str:
    """district/room_count karşılaştırmalarını case+whitespace-insensitive
    yapar — "Nilüfer" ile "nilüfer", "3+1" ile " 3+1 " aynı kabul edilmeli.
    Danışmanın/Gemini'nin/adayın yazdığı metin asla garanti aynı harf
    büyüklüğünde olmuyor; tam string eşleşmesi gerçek eşleşen portföyleri
    sessizce kaçırıyordu (bkz. matching_node docstring)."""
    return value.strip().lower()


def _normalize_room_count(value: str) -> str:
    """"3 + 1" / "3+1" gibi '+' etrafındaki boşluk varyasyonlarını "3+1"
    kalıbına indirger — _normalize tek başına bunu yakalamıyor, format farkı
    yüzünden birebir aynı daire tipi gerçek bir eşleşmeyi kaçırıyordu."""
    return _ROOM_SEPARATOR.sub("+", _normalize(value))


def matching_node(state: AgentState, db: Session) -> AgentState:
    """Sprint 1 MVP: vektör benzerliği değil, basit SQL filtresi.

    Bütçe aralığı + oda sayısı + bölge eşleşmesiyle uygun portföyleri döner.
    Bütçe filtresi ±%5 toleranslıdır (BUDGET_TOLERANCE_RATIO) — sınırın az
    üzerinde/altında kalan bir portföy artık tamamen elenmiyor, sadece
    match_reason'da bunu belirtiyoruz. `radius_km` set edilmişse ve lead'in
    bölgesi geocode edilebiliyorsa, tam bölge string eşleşmesi yerine coğrafi
    yarıçap filtresi uygulanır (bkz. app/agents/geocoding.py) — geocode
    başarısız olursa (ağ hatası, rate-limit, bilinmeyen bölge) o portföy için
    sessizce bölge string eşleşmesine düşülür (bölge adı aranan bölgeyle
    birebir aynıysa dahil edilir, değilse mesafe doğrulanamadığından atlanır;
    aksi halde tek bir Nominatim rate-limit hatası, aslında aranan bölgenin
    tam içindeki gerçek bir eşleşen portföyü de listeden düşürüyordu). Hem
    bölge hem oda sayısı karşılaştırmaları case/whitespace-insensitive
    (_normalize) — aksi halde "Nilüfer" ilanı "nilüfer" arayan bir lead'e
    hiç eşleşmiyordu (gerçek bir prod hatası, bkz. commit notu).
    Bölgesel emsal embedding tabanlı benzerlik Sprint 2'de Pricing Agent ile birlikte eklendi.
    """
    radius_km = state.get("radius_km")
    center = geocode_district(db, state["district"]) if radius_km and state.get("district") else None

    query = select(Listing).where(Listing.status == "active")
    if not center and state.get("district"):
        query = query.where(func.lower(func.trim(Listing.district)) == _normalize(state["district"]))
    if state.get("room_count"):
        target_room = _normalize_room_count(state["room_count"])
        query = query.where(
            func.regexp_replace(func.lower(func.trim(Listing.room_count)), r"\s*\+\s*", "+", "g")
            == target_room
        )

    budget_max = state.get("budget_max")
    budget_min = state.get("budget_min")
    if budget_max is not None:
        query = query.where(Listing.price <= budget_max * (1 + BUDGET_TOLERANCE_RATIO))
    if budget_min is not None:
        query = query.where(Listing.price >= budget_min * (1 - BUDGET_TOLERANCE_RATIO))

    listings = db.execute(query).scalars().all()

    target_district = _normalize(state["district"]) if state.get("district") else None

    candidates = []
    for listing in listings:
        distance = None
        if center:
            listing_coords = geocode_district(db, listing.district)
            if listing_coords is not None:
                distance = haversine_km(*center, *listing_coords)
                if distance > radius_km:
                    continue
            elif not target_district or _normalize(listing.district or "") != target_district:
                # Geocoding başarısız oldu ve bölge adı aranan bölgeyle
                # birebir aynı değil — mesafeyi doğrulayamadığımız için
                # güvenli tarafta kalıp bu portföyü atlıyoruz.
                continue

        reason = _build_match_reason(listing, distance, budget_max, budget_min)
        candidates.append(
            {
                "listing_id": str(listing.id),
                "title": listing.title,
                "price": float(listing.price),
                "match_reason": reason,
            }
        )

    state["candidate_listings"] = candidates
    return state


def _build_match_reason(listing: Listing, distance: float | None, budget_max, budget_min) -> str:
    if distance is not None:
        reason = f"{listing.district} bölgesi, aradığınız konuma ~{distance:.1f} km mesafede"
    else:
        reason = f"{listing.district} bölgesinde, bütçe ve oda sayısı kriterine uyuyor"

    price = float(listing.price)
    if budget_max is not None and price > budget_max:
        over_pct = round((price / budget_max - 1) * 100)
        reason += f" (bütçenin ~%{over_pct} üzerinde)"
    elif budget_min is not None and price < budget_min:
        under_pct = round((1 - price / budget_min) * 100)
        reason += f" (bütçenin ~%{under_pct} altında)"
    return reason
