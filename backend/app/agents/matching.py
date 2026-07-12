import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.geocoding import geocode_district, haversine_km
from app.agents.state import AgentState
from app.core.db import set_tenant
from app.core.text import fold_turkish_i
from app.models.listing import Listing

# Bütçenin biraz üzerinde/altında kalan ama aksi halde tam uyan bir portföyü
# tamamen elemek yerine "yakın eşleşme" olarak sunmak için tolerans payı —
# katı ≤/≥ filtresi ₺1 farkla bile gerçek uygun bir evi listeden düşürüyordu.
BUDGET_TOLERANCE_RATIO = 0.05

# Lead açıkça bir radius_km istemediğinde, string/başlık eşleşmesi bulunamayan
# bir portföyü coğrafi doğrulama için tarafsız bir güvenlik ağı yarıçapı —
# bir ilçe ölçeğini kapsayacak kadar geniş, alakasız uzak bir şehri/bölgeyi
# içine almayacak kadar dar (bkz. matching_node).
DEFAULT_FALLBACK_RADIUS_KM = 10

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

# property_type/listing_type migration'lardan (0020/0022) ÖNCE oluşturulan
# portföyler geriye dönük olarak "sale"/"residential" varsayılanı aldı — gerçek
# tipi farklı olsa bile (ör. "600 M2 KİRALIK İŞ YERİ" başlıklı bir ilan DB'de
# "residential" kalabiliyor, danışman panelden düzeltmediği sürece). Sert bir
# DB-kolonu filtresi böyle bir ilanı adayın gerçekte aradığı şeyle eşleşmesine
# rağmen sessizce elerdi (gerçek prod hatası, kullanıcı ekran görüntüsüyle
# bildirdi). Bu yüzden filtre DB kolonuyla uyuşmasa bile başlıkta hedef tipin
# anahtar kelimelerinden biri geçiyorsa yine de eşleşme sayar.
_LISTING_TYPE_TITLE_KEYWORDS = {
    "sale": ("satılık",),
    "rent": ("kiralık", "kiraya"),
}
_PROPERTY_TYPE_TITLE_KEYWORDS = {
    "residential": ("daire", "konut", "villa", "rezidans", "dubleks", "müstakil"),
    "commercial": ("iş yeri", "işyeri", "ofis", "dükkan", "mağaza", "depo", "büro", "plaza"),
    "land": ("arsa", "arazi"),
}


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


def _title_indicates_type(title: str | None, keywords: tuple[str, ...]) -> bool:
    if not title:
        return False
    normalized_title = _normalize(title)
    return any(keyword in normalized_title for keyword in keywords)


def _type_preference_matches(
    listing: Listing, listing_type_preference: str | None, property_type_preference: str | None
) -> bool:
    """listing_type_preference/property_type_preference set edilmişse eşleşme
    ister — ama DB kolonu uyuşmuyor diye hemen elemez: başlık hedef tipin
    anahtar kelimelerinden birini içeriyorsa (bkz. _PROPERTY_TYPE_TITLE_KEYWORDS/
    _LISTING_TYPE_TITLE_KEYWORDS) yine kabul eder (migration-öncesi yanlış
    varsayılan tip etiketine karşı güvenlik ağı, gerçek prod hatası)."""
    if listing_type_preference and listing.listing_type != listing_type_preference:
        if not _title_indicates_type(listing.title, _LISTING_TYPE_TITLE_KEYWORDS[listing_type_preference]):
            return False
    if property_type_preference and listing.property_type != property_type_preference:
        if not _title_indicates_type(listing.title, _PROPERTY_TYPE_TITLE_KEYWORDS[property_type_preference]):
            return False
    return True


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

    Konum doğrulaması artık İKİ katmanlı: (1) string/başlık eşleşmesi
    (_title_mentions_area) (2) bu da tutmazsa, lead açıkça bir radius_km
    istemiş olsun ya da olmasın, bir GÜVENLİK AĞI olarak coğrafi geocoding
    doğrulaması HER ZAMAN devreye girer (bkz. app/agents/geocoding.py) —
    radius_km verilmemişse DEFAULT_FALLBACK_RADIUS_KM kullanılır (kullanıcı
    talebi: "yapay zeka arkada bir sorgu daha atıp konumu doğrulasın", gerçek
    prod hatası — Gemini'nin district'e yazdığı bir ifade listing.district'le
    ne birebir ne de başlıkla fuzzy eşleşmediğinde önceden sessizce
    kaçırılıyordu). Lead'in KENDİ bölgesi hiç geocode edilemezse (ağ hatası,
    bilinmeyen/anlamsız ifade) eskisi gibi sadece string/başlık eşleşmesine
    güvenilir — coğrafi doğrulama hiç devreye girmez. Bir portföyün KENDİ
    geocode'u başarısız olursa (ama lead'inki başarılıysa) o portföy güvenli
    tarafta kalınıp atlanır (aksi halde tek bir Nominatim hatası, aranan
    bölgenin tam içindeki gerçek bir portföyü de listeden düşürüyordu). Hem
    bölge hem oda sayısı karşılaştırmaları case/whitespace-insensitive
    (_normalize).

    `listing_type_preference` (sale/rent) ve `property_type_preference`
    (residential/commercial/land) set edilmişse eşleşme ister — ama DB
    kolonuyla uyuşmuyor diye hemen elemez, başlıkta hedef tipin anahtar
    kelimesi geçiyorsa yine kabul eder (bkz. _type_preference_matches; migration
    0020/0022'den önce oluşturulan portföyler geriye dönük "sale"/"residential"
    varsayılanı aldığı için gerçek tipi farklı olabiliyordu — gerçek prod
    hatası, kullanıcı ekran görüntüsüyle bildirdi). None ise (belirtilmedi)
    hiçbir portföy bu kritere göre elenmez (recall-öncelikli felsefe: bilinmeyen
    tercihte fazla eşleşme az eşleşmeden iyidir, kullanıcı talebi).
    property_type_preference commercial/land ise room_count filtresi hiç
    uygulanmaz — oda sayısı kavramı bu tiplerde anlamsız (gerçek prod hatası:
    "kiralık iş yeri" arayan bir aday, alakasız bir room_count/budget yüzünden
    ticari bir portföyü kaçırabiliyordu, kullanıcı bildirdi).
    Bölgesel emsal embedding tabanlı benzerlik Sprint 2'de Pricing Agent ile birlikte eklendi.

    ÖNEMLİ (RLS/tenant context): geocode_district ilk kez geocode edilen bir
    bölge için geocoded_districts önbelleğine yazarken `db.commit()` çağırıyor
    — bu, `SET LOCAL app.current_office_id` ile set edilen tenant context'i
    SIFIRLIYOR (bkz. CLAUDE.md madde 2/7). Konum doğrulaması artık HER ZAMAN
    (radius_km olmasa bile) devreye girdiği için bu fonksiyon sonunda
    set_tenant TEKRAR çağrılıyor — aksi halde bu fonksiyondan sonra AYNI
    session'da çalışan tenant-scoped bir sorgu (ör. listings sorgusunun
    kendisi ya da çağıran route'un match sonrası çalıştırdığı bir sorgu)
    sessizce boş dönerdi (gerçek bir regresyon, bu değişiklik sırasında
    testlerde yakalandı — bkz. app/agents/intake.py: _maybe_extract_and_apply
    aynı deseni zaten uyguluyor).
    """
    target_area = state.get("district")
    center = geocode_district(db, target_area) if target_area else None
    # geocode_district bir cache-miss'te commit yapmış olabilir (yukarıdaki
    # docstring) — SET LOCAL tenant context'i, aşağıdaki listings sorgusundan
    # ÖNCE burada tekrar kurulmalı, aksi halde o sorgu sessizce boş döner.
    set_tenant(db, state["office_id"])
    effective_radius_km = state.get("radius_km") or DEFAULT_FALLBACK_RADIUS_KM
    listing_type_preference = state.get("listing_type_preference")
    property_type_preference = state.get("property_type_preference")

    query = select(Listing).where(Listing.status == "active")
    if state.get("room_count") and property_type_preference not in _ROOM_COUNT_EXEMPT_PROPERTY_TYPES:
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

    target_district = _normalize(target_area) if target_area else None

    candidates = []
    for listing in listings:
        if not _type_preference_matches(listing, listing_type_preference, property_type_preference):
            continue

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
            if distance > effective_radius_km:
                continue
        elif not center and target_district and not area_matched:
            continue

        reason = _build_match_reason(listing, distance, budget_max, budget_min, area_matched)
        candidates.append(
            {
                "listing_id": str(listing.id),
                "title": listing.title,
                "price": float(listing.price),
                # WhatsApp mesajlarındaki temiz payload (fiyat/oda/konum/link)
                # için — bkz. app/agents/match_payload.py: strip_match_payload.
                "room_count": listing.room_count,
                "district": listing.district,
                "city": listing.city,
                "match_reason": reason,
            }
        )

    state["candidate_listings"] = candidates
    # geocode_district çağrıları (yukarıda) bir cache-miss'te commit yapmış
    # olabilir — aynı session'da bu fonksiyondan SONRA çalışacak tenant-scoped
    # sorgular için context'i güvenceye alıyoruz (bkz. yukarıdaki docstring).
    set_tenant(db, state["office_id"])
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
