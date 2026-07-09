"""Türkiye il/ilçe/mahalle sözlüğü ve konum çözümleme yardımcıları.

Veri, repo içine gömülü statik bir sözlükten gelir (app/data/tr_geo.json.gz —
81 il, 973 ilçe, ~32k mahalle). Harici API/DB yok: ilk erişimde bir kez
belleğe açılır (~400KB JSON), tüm aramalar bellek içinde prefix taramasıdır.

İki tüketici var:
- /geo/* route'ları: ilan formundaki şehir→ilçe→mahalle otomatik tamamlama.
- listing_import + create_listing: portal kaynağından/elle girilen ilçe-mahalle
  bilgisinden şehri çıkarmak (infer_city) ve serbest metin konum parçalarını
  yapılandırılmış alanlara oturtmak (resolve_location).
"""
import gzip
import json
import re
from functools import lru_cache
from pathlib import Path

from app.core.text import fold_turkish_i

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "tr_geo.json.gz"

# "Caferağa Mah." / "Moda Mahallesi" gibi ekler dataset'teki çıplak adla
# eşleşmeyi bozar — çözümlemeden önce temizlenir.
_NEIGHBORHOOD_SUFFIX = re.compile(r"\s*(mahallesi|mahalle|mah\.?|mh\.?)\s*$", re.IGNORECASE)

# Aksansız yazıma tolerans: kullanıcı/portal "kadikoy" da yazabilir,
# "Kadıköy" de. fold_turkish_i İ/I/ı'yı hallediyor; kalan Türkçe harfler
# burada ASCII karşılığına indirilir ki iki yazım da aynı anahtara düşsün.
_DIACRITICS = str.maketrans("çğöşü", "cgosu")


def _fold(text: str) -> str:
    return fold_turkish_i(text).translate(_DIACRITICS)


@lru_cache(maxsize=1)
def _data() -> dict[str, dict[str, list[str]]]:
    with gzip.open(_DATA_PATH, "rt", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _city_by_fold() -> dict[str, str]:
    return {_fold(city): city for city in _data()}


@lru_cache(maxsize=1)
def _district_index() -> dict[str, dict[str, str]]:
    """fold(ilçe) → {il: kanonik ilçe adı}. Aynı ilçe adı birden fazla ilde
    olabilir ("Merkez" 51 ilde var) — infer_city bu yüzden mahalleyle
    ayrıştırmayı dener."""
    index: dict[str, dict[str, str]] = {}
    for city, districts in _data().items():
        for district in districts:
            index.setdefault(_fold(district), {})[city] = district
    return index


def _clean_part(text: str) -> str:
    return _NEIGHBORHOOD_SUFFIX.sub("", text.strip())


def _prefix_matches(names: list[str], query: str, limit: int) -> list[str]:
    folded_query = _fold(query.strip())
    matches = sorted((n for n in names if _fold(n).startswith(folded_query)), key=_fold)
    return matches[:limit]


def search_cities(query: str = "", limit: int = 20) -> list[str]:
    return _prefix_matches(list(_data()), query, limit)


def canonical_city(name: str) -> str | None:
    return _city_by_fold().get(_fold(name.strip()))


def search_districts(query: str = "", city: str | None = None, limit: int = 20) -> list[str]:
    if city:
        canonical = canonical_city(city)
        names = list(_data().get(canonical, {})) if canonical else []
    else:
        # Şehir seçilmeden ilçe aranırsa tüm iller taranır; ad çakışmaları
        # tek sonuca indirilir (frontend şehri zaten önce seçtiriyor).
        names = sorted({d for districts in _data().values() for d in districts})
    return _prefix_matches(names, query, limit)


def search_neighborhoods(
    query: str = "", city: str | None = None, district: str | None = None, limit: int = 30
) -> list[str]:
    if not district:
        return []
    entry = _district_index().get(_fold(_clean_part(district)), {})
    if city:
        canonical = canonical_city(city)
        cities = [canonical] if canonical and canonical in entry else []
    else:
        cities = list(entry)
    names = sorted({n for c in cities for n in _data()[c][entry[c]]})
    return _prefix_matches(names, query, limit)


def infer_city(district: str, neighborhood: str | None = None) -> str | None:
    """İlçe (ve varsa mahalle) adından ili bulur. İlçe adı birden fazla ilde
    geçiyorsa mahalleyle ayrıştırılır; hâlâ belirsizse None (yanlış il
    etiketlemektense boş bırakmak tercih edilir)."""
    entry = _district_index().get(_fold(_clean_part(district)))
    if not entry:
        return None
    if len(entry) == 1:
        return next(iter(entry))
    if neighborhood:
        folded = _fold(_clean_part(neighborhood))
        candidates = [
            city
            for city, canonical_district in entry.items()
            if any(_fold(n) == folded for n in _data()[city][canonical_district])
        ]
        if len(candidates) == 1:
            return candidates[0]
    return None


def resolve_location(parts: list[str]) -> dict[str, str | None]:
    """Portal sayfasından gelen serbest metin konum parçalarını ("İstanbul /
    Kadıköy / Caferağa Mah.") il/ilçe/mahalle alanlarına oturtur. Best-effort:
    dataset'le eşleşmeyen parça, konumuna göre en olası alana ham haliyle
    yazılır; il hiç gelmediyse ilçe+mahalleden çıkarılır."""
    city: str | None = None
    district: str | None = None
    neighborhood: str | None = None

    unmatched: list[str] = []
    seen: set[str] = set()
    for raw in parts:
        cleaned = _clean_part(raw)
        if not cleaned:
            continue
        folded = _fold(cleaned)
        # Aynı parça birden fazla kaynakta (adres alanı + breadcrumb) tekrar
        # gelebilir — ikinci geçişin mahalle sanılmaması için tekilleştirilir.
        if folded in seen:
            continue
        seen.add(folded)
        if city is None:
            matched_city = canonical_city(cleaned)
            if matched_city:
                city = matched_city
                continue
        if district is None:
            entry = _district_index().get(folded)
            if entry and (city is None or city in entry):
                district = entry[city] if city else entry[next(iter(entry))]
                continue
        unmatched.append(cleaned)

    # Eşleşmeyen parçalar: ilçe boşsa ilki ilçe kabul edilir, kalan son parça
    # mahalledir (portallar konumu il→ilçe→mahalle sırasıyla verir).
    if district is None and unmatched:
        district = unmatched.pop(0)
    if unmatched:
        neighborhood = unmatched[-1]

    if city is None and district:
        city = infer_city(district, neighborhood)

    # Mahalle dataset'te varsa kanonik yazımıyla döndürülür ("Fenerbahce" →
    # "Fenerbahçe"); yoksa ham haliyle kalır (best-effort, danışman düzeltir).
    if neighborhood and district:
        matches = search_neighborhoods(neighborhood, city=city, district=district, limit=1)
        if matches and _fold(matches[0]) == _fold(neighborhood):
            neighborhood = matches[0]

    return {"city": city, "district": district, "neighborhood": neighborhood}
