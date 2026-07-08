import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.geocoding import geocode_district, haversine_km
from app.agents.state import AgentState
from app.core.text import fold_turkish_i
from app.models.listing import Listing

# Bütçenin biraz üzerinde/altında kalan ama aksi halde tam uyan bir portföyü
# tamamen elemek yerine "yakın eşleşme" olarak sunmak için tolerans payı —
# katı ≤/≥ filtresi ₺1 farkla bile gerçek uygun bir evi listeden düşürüyordu.
BUDGET_TOLERANCE_RATIO = 0.05

_ROOM_SEPARATOR = re.compile(r"\s*\+\s*")

# Konum eşleştirmesinde tam alan ifadesi başlıkta geçmiyorsa (ör. Gemini'nin
# district'e bir cadde/sokak adı yazdığı durumlarda) kelime bazında ortak-önek
# karşılaştırmasına düşülür — bu jenerik son ekler anlam taşımadığı için
# kıyaslamadan önce ayıklanır (bkz. _significant_words).
_LOCATION_SUFFIX_WORDS = {
    "cadde", "caddesi", "sokak", "sokağı", "sokagi", "bulvar", "bulvarı", "bulvari",
    "mahalle", "mahallesi", "köy", "köyü", "koy", "koyu",
}
_MIN_FUZZY_WORD_LEN = 3
_MIN_SHARED_PREFIX = 5

# Oda sayısının anlamsız olduğu emlak tipleri — bu tiplerde room_count filtresi
# hiç uygulanmaz (bkz. matching_node).
_ROOM_COUNT_EXEMPT_PROPERTY_TYPES = {"commercial", "land"}


def _normalize(value: str) -> str:
    """district/room_count karşılaştırmalarını case+whitespace-insensitive
    yapar — "Nilüfer" ile "nilüfer", "3+1" ile " 3+1 " aynı kabul edilmeli.
    fold_turkish_i kullanıyor (sadece basit .lower() değil) çünkü "İzmir" gibi
    büyük Türkçe İ içeren bir bölge adı da aynı sessiz eşleştirme hatasına
    düşebilirdi (bkz. app/core/text.py, app/agents/listing_import.py)."""
    return fold_turkish_i(value.strip())


def _normalize_room_count(value: str) -> str:
    """"3 + 1" / "3+1" gibi '+' etrafındaki boşluk varyasyonlarını "3+1"
    kalıbına indirger — _normalize tek başına bunu yakalamıyor, format farkı
    yüzünden birebir aynı daire tipi gerçek bir eşleşmeyi kaçırıyordu."""
    return _ROOM_SEPARATOR.sub("+", _normalize(value))


def _significant_words(value: str) -> list[str]:
    return [
        word
        for word in _normalize(value).split()
        if word not in _LOCATION_SUFFIX_WORDS and len(word) >= _MIN_FUZZY_WORD_LEN
    ]


def _words_share_prefix(word_a: str, word_b: str) -> bool:
    shorter, longer = (word_a, word_b) if len(word_a) <= len(word_b) else (word_b, word_a)
    prefix_len = min(len(shorter), _MIN_SHARED_PREFIX)
    return longer.startswith(shorter[:prefix_len])


def _title_mentions_area(title: str | None, area: str) -> bool:
    """Sahibinden'in konum alanı genelde sadece il/ilçe düzeyinde (örn. "Bursa
    / Osmangazi") — mahalle bilgisi (örn. "Çekirge") neredeyse hep ilanın
    BAŞLIĞINDA geçer ("ÇEKİRGEDE SATILIK..."). Lead "Çekirge" arıyorsa ve
    hiçbir listing.district buna birebir uymuyorsa (hepsi "Osmangazi"), gerçek
    bir eşleşme sessizce kaçırılır — bu yüzden başlığı da tarıyoruz (gerçek
    prod hatası, kullanıcı bildirdi).

    Tam ifade birebir geçmiyorsa kelime bazında ortak-önek karşılaştırmasına
    düşülür: Gemini'nin district alanına bir cadde/sokak adı yazdığı durumlarda
    (ör. "Uluyol Caddesi") Türkçe hal ekleri ("Uluyol**a** Yakın") birebir
    substring eşleşmesini kırıyordu — bu da gerçek bir prod hatası (kullanıcı
    bildirdi). cadde/sokak/mahalle gibi jenerik kelimeler ayıklanıp kalan
    anlamlı kelimeler için ilk ~5 karakter ortak mı diye bakılır."""
    if not title or not area.strip():
        return False
    normalized_title = _normalize(title)
    if _normalize(area) in normalized_title:
        return True
    title_words = normalized_title.split()
    return any(
        _words_share_prefix(area_word, title_word)
        for area_word in _significant_words(area)
        for title_word in title_words
    )


def matching_node(state: AgentState, db: Session) -> AgentState:
    """Sprint 1 MVP: vektör benzerliği değil, basit SQL filtresi + Python-side
    bölge eşleştirmesi.

    Bütçe aralığı + oda sayısı + bölge eşleşmesiyle uygun portföyleri döner.
    Bütçe filtresi ±%5 toleranslıdır (BUDGET_TOLERANCE_RATIO) — sınırın az
    üzerinde/altında kalan bir portföy artık tamamen elenmiyor, sadece
    match_reason'da bunu belirtiyoruz.

    Bölge eşleşmesi artık İKİ sinyale bakıyor: listing.district (il/ilçe
    düzeyinde, ör. "Osmangazi") VE listing.title (mahalle düzeyinde, ör.
    "ÇEKİRGEDE SATILIK..." — Sahibinden'in konum alanı sadece il/ilçe
    gösterdiği için mahalle adı neredeyse hep başlıkta geçer, bkz.
    _title_mentions_area). Bu sayede lead "Çekirge" ararken listing.district
    sadece "Osmangazi" olsa bile başlığında "Çekirge" geçen bir portföy artık
    kaçırılmıyor (gerçek prod hatası, kullanıcı bildirdi).

    `radius_km` set edilmişse ve lead'in bölgesi geocode edilebiliyorsa, bu iki
    sinyalden biri zaten eşleşmiyorsa coğrafi yarıçap filtresi uygulanır (bkz.
    app/agents/geocoding.py) — geocode başarısız olursa (ağ hatası, rate-limit,
    bilinmeyen bölge) o portföy güvenli tarafta kalınıp atlanır (aksi halde tek
    bir Nominatim hatası, aranan bölgenin tam içindeki gerçek bir portföyü de
    listeden düşürüyordu). Hem bölge hem oda sayısı karşılaştırmaları
    case/whitespace-insensitive (_normalize).

    `listing_type_preference` (sale/rent) ve `property_type_preference`
    (residential/commercial/land) set edilmişse sert filtre uygular — None ise
    (belirtilmedi) hiçbir portföy bu kritere göre elenmez (recall-öncelikli
    felsefe: bilinmeyen tercihte fazla eşleşme az eşleşmeden iyidir, kullanıcı
    talebi). property_type_preference commercial/land ise room_count filtresi
    hiç uygulanmaz — oda sayısı kavramı bu tiplerde anlamsız (gerçek prod
    hatası: "kiralık iş yeri" arayan bir aday, alakasız bir room_count/budget
    yüzünden ticari bir portföyü kaçırabiliyordu, kullanıcı bildirdi).
    Bölgesel emsal embedding tabanlı benzerlik Sprint 2'de Pricing Agent ile birlikte eklendi.
    """
    radius_km = state.get("radius_km")
    center = geocode_district(db, state["district"]) if radius_km and state.get("district") else None
    property_type_preference = state.get("property_type_preference")

    query = select(Listing).where(Listing.status == "active")
    if state.get("room_count") and property_type_preference not in _ROOM_COUNT_EXEMPT_PROPERTY_TYPES:
        target_room = _normalize_room_count(state["room_count"])
        query = query.where(
            func.regexp_replace(func.lower(func.trim(Listing.room_count)), r"\s*\+\s*", "+", "g")
            == target_room
        )
    if state.get("listing_type_preference"):
        query = query.where(Listing.listing_type == state["listing_type_preference"])
    if property_type_preference:
        query = query.where(Listing.property_type == property_type_preference)

    budget_max = state.get("budget_max")
    budget_min = state.get("budget_min")
    if budget_max is not None:
        query = query.where(Listing.price <= budget_max * (1 + BUDGET_TOLERANCE_RATIO))
    if budget_min is not None:
        query = query.where(Listing.price >= budget_min * (1 - BUDGET_TOLERANCE_RATIO))

    listings = db.execute(query).scalars().all()

    target_area = state.get("district")
    target_district = _normalize(target_area) if target_area else None

    candidates = []
    for listing in listings:
        distance = None
        area_matched = bool(target_district) and (
            _normalize(listing.district or "") == target_district
            or _title_mentions_area(listing.title, target_area)
        )

        if center and not area_matched:
            listing_coords = geocode_district(db, listing.district)
            if listing_coords is None:
                # Bölge/başlık eşleşmesi yok, mesafe de doğrulanamadı —
                # güvenli tarafta kalıp bu portföyü atlıyoruz.
                continue
            distance = haversine_km(*center, *listing_coords)
            if distance > radius_km:
                continue
        elif not center and target_district and not area_matched:
            continue

        reason = _build_match_reason(listing, distance, budget_max, budget_min, area_matched)
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


def _build_match_reason(
    listing: Listing, distance: float | None, budget_max, budget_min, area_matched: bool
) -> str:
    if distance is not None:
        reason = f"{listing.district} bölgesi, aradığınız konuma ~{distance:.1f} km mesafede"
    elif area_matched:
        reason = f"{listing.district} bölgesinde (veya başlığında), bütçe ve oda sayısı kriterine uyuyor"
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
