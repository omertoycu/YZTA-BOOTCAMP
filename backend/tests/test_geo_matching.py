import uuid

from app.agents import geocoding, matching

FAKE_COORDS = {
    "kadikoy": (40.9833, 29.0333),
    "uskudar": (41.0225, 29.0244),  # Kadıköy'e ~5km yakın
    "sisli": (41.5000, 29.9000),  # Kadıköy'den ~90km uzak (test amaçlı abartılı)
}


def _fake_geocode(db, district):
    if not district:
        return None
    return FAKE_COORDS.get(district.strip().lower())


def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "Supersecret123!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_radius_match_includes_nearby_excludes_far(client, monkeypatch):
    monkeypatch.setattr(matching, "geocode_district", _fake_geocode)

    headers = _register(client, "Ofis Geo Test 1", "owner1@geo-test.com")
    client.post(
        "/listings",
        json={"title": "Yakın ilan", "district": "Uskudar", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    client.post(
        "/listings",
        json={"title": "Uzak ilan", "district": "Sisli", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )

    lead_resp = client.post(
        "/leads",
        json={"contact_phone": "5551112233", "district": "Kadikoy", "radius_km": 10},
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    titles = {m["title"] for m in match_resp.json()}
    assert titles == {"Yakın ilan"}


def test_match_without_radius_falls_back_to_default_geocoding_safety_net(client, monkeypatch):
    """Davranış kasıtlı olarak değişti (kullanıcı talebi: "yapay zeka arkada
    bir sorgu daha atıp konumu doğrulasın"). Artık radius_km verilmese bile,
    string/başlık eşleşmesi bulamayan bir portföy için DEFAULT_FALLBACK_RADIUS_KM
    yarıçapıyla bir coğrafi doğrulama güvenlik ağı devreye girer — yakın farklı
    bir ilçe (Üsküdar, Kadıköy'e ~5km) artık dahil edilir, gerçekten uzak bir
    bölge (Şişli, ~90km) yine elenir."""
    monkeypatch.setattr(matching, "geocode_district", _fake_geocode)

    headers = _register(client, "Ofis Geo Test 2", "owner2@geo-test.com")
    client.post(
        "/listings",
        json={"title": "Tam eşleşme", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    client.post(
        "/listings",
        json={"title": "Yakın farklı bölge", "district": "Uskudar", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    client.post(
        "/listings",
        json={"title": "Çok uzak bölge", "district": "Sisli", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    lead_resp = client.post(
        "/leads",
        json={"contact_phone": "5551112244", "district": "Kadikoy"},
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    titles = {m["title"] for m in match_resp.json()}
    assert titles == {"Tam eşleşme", "Yakın farklı bölge"}


def test_match_without_radius_and_ungeocodable_lead_district_keeps_exact_match_only(client, monkeypatch):
    """Lead'in KENDİ bölgesi hiç geocode edilemezse (ör. anlamsız/bilinmeyen
    bir ifade), coğrafi güvenlik ağı hiç devreye girmemeli — eski (sadece
    string/başlık eşleşmesi) davranış korunmalı."""
    monkeypatch.setattr(matching, "geocode_district", lambda db, district: None)

    headers = _register(client, "Ofis Geo Test 2b", "owner2b@geo-test.com")
    client.post(
        "/listings",
        json={"title": "Tam eşleşme", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    client.post(
        "/listings",
        json={"title": "Farklı bölge", "district": "Uskudar", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    lead_resp = client.post(
        "/leads",
        json={"contact_phone": "5551112245", "district": "Kadikoy"},
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    titles = {m["title"] for m in match_resp.json()}
    assert titles == {"Tam eşleşme"}


def test_match_without_radius_is_case_and_whitespace_insensitive(client, monkeypatch):
    """Gerçek prod hatası: lead'in bölgesi 'nilüfer' (küçük harf), ilanın
    bölgesi 'Nilüfer' (büyük N) yazılınca tam string eşleşmesi eşleşen bir
    ilanı sessizce kaçırıyordu. district VE room_count karşılaştırması artık
    case/whitespace-insensitive olmalı."""
    monkeypatch.setattr(matching, "geocode_district", lambda db, district: None)

    headers = _register(client, "Ofis Geo Test 4", "owner4@geo-test.com")
    client.post(
        "/listings",
        json={"title": "Büyük harfli ilan", "district": "Nilüfer", "price": 15000, "room_count": " 3+1 "},
        headers=headers,
    )
    lead_resp = client.post(
        "/leads",
        json={"contact_phone": "5551112266", "district": "nilüfer", "room_count": "3+1"},
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    titles = {m["title"] for m in match_resp.json()}
    assert titles == {"Büyük harfli ilan"}


def test_geocode_failure_falls_back_to_exact_district_match(client, monkeypatch):
    """Lead'in bölgesi geocode edilemiyorsa (None dönerse) sert hata yerine
    eski bölge string eşleşmesine sessizce düşülmeli."""
    monkeypatch.setattr(matching, "geocode_district", lambda db, district: None)

    headers = _register(client, "Ofis Geo Test 3", "owner3@geo-test.com")
    client.post(
        "/listings",
        json={"title": "Bilinmeyen bölge ilanı", "district": "Bilinmeyenbolge", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    lead_resp = client.post(
        "/leads",
        json={"contact_phone": "5551112255", "district": "Bilinmeyenbolge", "radius_km": 5},
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    titles = {m["title"] for m in match_resp.json()}
    assert titles == {"Bilinmeyen bölge ilanı"}


def test_per_listing_geocode_failure_falls_back_to_same_district_match(client, monkeypatch):
    """Gerçek prod hatası: radius aramasında bir portföyün geocode'u ağ
    hatası/Nominatim rate-limit'i yüzünden başarısız olursa, sistem onu
    sessizce eliyordu — bölgesi aranan bölgeyle birebir aynı olsa bile.
    Böyle bir portföy artık dahil edilmeli; sadece bölgesi de farklıysa
    (mesafe hiç doğrulanamadığı için) atlanmalı."""

    def _partial_geocode(db, district):
        normalized = (district or "").strip().lower()
        if normalized == "kadikoy":
            return FAKE_COORDS["kadikoy"]
        return None  # diğer tüm bölgeler için geocode "başarısız" simüle edilir

    monkeypatch.setattr(matching, "geocode_district", _partial_geocode)

    headers = _register(client, "Ofis Geo Test 5", "owner5@geo-test.com")
    client.post(
        "/listings",
        json={"title": "Aynı bölge, geocode başarısız", "district": "Kadikoy", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    client.post(
        "/listings",
        json={"title": "Farklı bölge, geocode başarısız", "district": "Besiktas", "price": 15000, "room_count": "2+1"},
        headers=headers,
    )

    lead_resp = client.post(
        "/leads",
        json={"contact_phone": "5551112277", "district": "Kadikoy", "radius_km": 10},
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    titles = {m["title"] for m in match_resp.json()}
    assert titles == {"Aynı bölge, geocode başarısız"}


def test_room_count_matches_regardless_of_plus_spacing(client, monkeypatch):
    """"3 + 1" (boşluklu) ile "3+1" aynı daire tipi sayılmalı — format farkı
    yüzünden birebir aynı daire tipi gerçek bir eşleşmeyi kaçırıyordu."""
    monkeypatch.setattr(matching, "geocode_district", lambda db, district: None)

    headers = _register(client, "Ofis Geo Test 6", "owner6@geo-test.com")
    client.post(
        "/listings",
        json={"title": "Boşluklu oda sayısı", "district": "Kadikoy", "price": 15000, "room_count": "3 + 1"},
        headers=headers,
    )
    lead_resp = client.post(
        "/leads",
        json={"contact_phone": "5551112288", "district": "Kadikoy", "room_count": "3+1"},
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    titles = {m["title"] for m in match_resp.json()}
    assert titles == {"Boşluklu oda sayısı"}


def test_budget_slightly_over_max_still_matches_with_tolerance(client, monkeypatch):
    """Bütçenin ~%3 üzerindeki bir portföy artık tamamen elenmek yerine
    ±%5 tolerans payı içinde "yakın eşleşme" olarak sunulmalı."""
    monkeypatch.setattr(matching, "geocode_district", lambda db, district: None)

    headers = _register(client, "Ofis Geo Test 7", "owner7@geo-test.com")
    client.post(
        "/listings",
        json={"title": "Bütçenin biraz üzerinde", "district": "Kadikoy", "price": 10300, "room_count": "2+1"},
        headers=headers,
    )
    client.post(
        "/listings",
        json={"title": "Bütçenin çok üzerinde", "district": "Kadikoy", "price": 20000, "room_count": "2+1"},
        headers=headers,
    )
    lead_resp = client.post(
        "/leads",
        json={"contact_phone": "5551112299", "district": "Kadikoy", "budget_max": 10000},
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    matches = match_resp.json()
    titles = {m["title"] for m in matches}
    assert titles == {"Bütçenin biraz üzerinde"}
    over_budget_match = next(m for m in matches if m["title"] == "Bütçenin biraz üzerinde")
    assert "üzerinde" in over_budget_match["match_reason"]


def test_haversine_km_known_distance():
    kadikoy = (40.9833, 29.0333)
    ankara = (39.9334, 32.8597)
    distance = geocoding.haversine_km(*kadikoy, *ankara)
    assert 320 < distance < 380  # gerçek mesafe ~350km


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeHttpClient:
    def __init__(self, payload):
        self._payload = payload
        self.call_count = 0

    def get(self, url, params=None):
        self.call_count += 1
        return _FakeResponse(self._payload)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_geocode_district_caches_after_first_lookup(db_session, monkeypatch):
    # geocoded_districts test'ler arası truncate edilmiyor (kalıcı bir önbellek
    # olduğu için bilinçli) — çakışmayı önlemek için her çalıştırmada benzersiz isim.
    district_name = f"TestBenzersizBolge-{uuid.uuid4().hex[:8]}"
    fake_client = _FakeHttpClient([{"lat": "40.99", "lon": "29.03"}])
    monkeypatch.setattr(geocoding, "get_http_client", lambda: fake_client)

    first = geocoding.geocode_district(db_session, district_name)
    assert first == (40.99, 29.03)
    assert fake_client.call_count == 1

    # İkinci çağrı önbellekten dönmeli, tekrar HTTP isteği atmamalı.
    second = geocoding.geocode_district(db_session, district_name.lower())
    assert second == (40.99, 29.03)
    assert fake_client.call_count == 1


def test_matches_via_neighborhood_mentioned_in_title_when_district_field_is_coarser(client, monkeypatch):
    """Gerçek prod hatası (kullanıcı bildirdi): "Bursa Osmangazi Çekirge"
    bölgesinde ev arandığında, Çekirge'de gerçek bir ilan olmasına rağmen
    sistem eşleşme bulamadı — çünkü Sahibinden'in konum alanı sadece il/ilçe
    düzeyinde ("Osmangazi"), mahalle adı ("Çekirge") sadece başlıkta geçiyor.
    Artık başlık da taranmalı."""
    monkeypatch.setattr(matching, "geocode_district", lambda db, district: None)

    headers = _register(client, "Ofis Mahalle Test 1", "owner1@mahalle-test.com")
    client.post(
        "/listings",
        json={
            "title": "BEGO GAYRİMENKULDEN ÇEKİRGEDE ACİL SATILIK ARSA",
            "district": "Osmangazi",
            "price": 900000,
            "room_count": "2+1",
        },
        headers=headers,
    )
    client.post(
        "/listings",
        json={
            "title": "Elmasbahçelerde satılık daire",
            "district": "Osmangazi",
            "price": 900000,
            "room_count": "2+1",
        },
        headers=headers,
    )

    lead_resp = client.post(
        "/leads",
        json={"contact_phone": "5551113300", "district": "Çekirge", "room_count": "2+1"},
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    titles = {m["title"] for m in match_resp.json()}
    assert titles == {"BEGO GAYRİMENKULDEN ÇEKİRGEDE ACİL SATILIK ARSA"}


def test_matches_via_title_even_with_radius_search(client, monkeypatch):
    """Aynı mahalle-başlık sinyali radius aramasında da devreye girmeli —
    başlıkta bölge adı geçen bir portföy için mesafe hesaplamaya bile gerek
    yok, doğrudan eşleşme kabul edilmeli."""

    def _geocode_only_center(db, district):
        if (district or "").strip().lower() == "çekirge":
            return (40.19, 29.02)
        return None  # diğer tüm bölgeler (ör. Osmangazi'nin kendisi) için "başarısız"

    monkeypatch.setattr(matching, "geocode_district", _geocode_only_center)

    headers = _register(client, "Ofis Mahalle Test 2", "owner2@mahalle-test.com")
    client.post(
        "/listings",
        json={
            "title": "Çekirgede satılık daire",
            "district": "Osmangazi",
            "price": 900000,
            "room_count": "2+1",
        },
        headers=headers,
    )

    lead_resp = client.post(
        "/leads",
        json={"contact_phone": "5551113311", "district": "Çekirge", "room_count": "2+1", "radius_km": 5},
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    titles = {m["title"] for m in match_resp.json()}
    assert titles == {"Çekirgede satılık daire"}


def test_listing_type_preference_excludes_wrong_transaction_type(client, monkeypatch):
    """Gerçek prod hatası (kullanıcı bildirdi): kiralık arayan bir adaya
    sistem satılık bir ilan da önerebiliyordu — Lead'de bu tercihi tutan alan
    yoktu. Artık listing_type_preference set edilince yanlış işlem tipi
    (satılık/kiralık) tamamen elenmeli."""
    monkeypatch.setattr(matching, "geocode_district", lambda db, district: None)

    headers = _register(client, "Ofis Tip Test 1", "owner1@tip-test.com")
    client.post(
        "/listings",
        json={
            "title": "Kiralık daire",
            "district": "Osmangazi",
            "price": 15000,
            "room_count": "2+1",
            "listing_type": "rent",
        },
        headers=headers,
    )
    client.post(
        "/listings",
        json={
            "title": "Satılık daire",
            "district": "Osmangazi",
            "price": 15000,
            "room_count": "2+1",
            "listing_type": "sale",
        },
        headers=headers,
    )

    lead_resp = client.post(
        "/leads",
        json={
            "contact_phone": "5551114400",
            "district": "Osmangazi",
            "room_count": "2+1",
            "listing_type_preference": "rent",
        },
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    titles = {m["title"] for m in match_resp.json()}
    assert titles == {"Kiralık daire"}


def test_property_type_preference_matches_via_title_when_db_column_is_stale(client, monkeypatch):
    """Gerçek prod hatası (kullanıcı ekran görüntüsüyle bildirdi): migration
    0022'den önce oluşturulmuş (ya da danışmanın hiç düzeltmediği) bir ilan
    DB'de "residential" (varsayılan) kalabiliyor, başlığı açıkça "İŞ YERİ" dese
    bile. Bir önceki düzeltmedeki SERT property_type filtresi böyle bir ilanı
    tam da bu yüzden elemeye başlamıştı — artık başlıkta hedef tipin anahtar
    kelimesi ("iş yeri") geçtiği için DB kolonu "residential" kalsa bile
    eşleşme kabul edilmeli."""
    monkeypatch.setattr(matching, "geocode_district", lambda db, district: None)

    headers = _register(client, "Ofis Tip Test 3", "owner3-stale@tip-test.com")
    client.post(
        "/listings",
        json={
            "title": "BEGO GAYRİMENKULDEN ULUYOLA YAKIN 600 M2 KİRALIK İŞ YERİ",
            "district": "Osmangazi",
            "price": 30000,
            "room_count": "Belirtilmedi",
            "listing_type": "rent",
            # property_type kasıtlı olarak gönderilmedi — migration-öncesi bir
            # ilanı taklit etmek için varsayılan "residential" kalıyor.
        },
        headers=headers,
    )

    lead_resp = client.post(
        "/leads",
        json={
            "contact_phone": "5551114433",
            "district": "Osmangazi",
            "listing_type_preference": "rent",
            "property_type_preference": "commercial",
        },
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    titles = {m["title"] for m in match_resp.json()}
    assert titles == {"BEGO GAYRİMENKULDEN ULUYOLA YAKIN 600 M2 KİRALIK İŞ YERİ"}


def test_commercial_property_type_skips_room_count_filter(client, monkeypatch):
    """Gerçek prod hatası (kullanıcı bildirdi): "kiralık iş yeri" arayan bir
    adayın lead kaydında alakasız/eksik bir room_count varsa (ör. önceki bir
    konut aramasından kalma), ticari bir portföy oda sayısı uyuşmadığı için
    yanlışlıkla elenebiliyordu. property_type_preference "commercial" ise
    room_count filtresi hiç uygulanmamalı."""
    monkeypatch.setattr(matching, "geocode_district", lambda db, district: None)

    headers = _register(client, "Ofis Tip Test 2", "owner2@tip-test.com")
    client.post(
        "/listings",
        json={
            "title": "BEGO GAYRİMENKULDEN ULUYOLA YAKIN 600 M2 KİRALIK İŞ YERİ",
            "district": "Osmangazi",
            "price": 30000,
            "room_count": "Belirtilmedi",
            "listing_type": "rent",
            "property_type": "commercial",
        },
        headers=headers,
    )

    lead_resp = client.post(
        "/leads",
        json={
            "contact_phone": "5551114411",
            "district": "Osmangazi",
            "room_count": "3+1",  # alakasız/eski bir aramadan kalma
            "listing_type_preference": "rent",
            "property_type_preference": "commercial",
        },
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    titles = {m["title"] for m in match_resp.json()}
    assert titles == {"BEGO GAYRİMENKULDEN ULUYOLA YAKIN 600 M2 KİRALIK İŞ YERİ"}


def test_matches_via_fuzzy_street_name_with_turkish_suffix(client, monkeypatch):
    """Gerçek prod hatası (kullanıcı bildirdi): "BEGO GAYRİMENKULDEN ULUYOLA
    YAKIN 600 M2 KİRALIK İŞ YERİ" ilanı, "uluyol caddesinde kiralık iş yeri"
    diyen bir adaya eşleşme olarak sunulmadı. Gemini'nin district'e ("mahalle/
    ilçe" yerine) bir cadde adı ("Uluyol Caddesi") yazması muhtemeldi — bu ne
    listing.district ("Osmangazi") ile birebir eşleşiyor ne de eski birebir
    substring kontrolüyle başlıktaki "ULUYOL**A**" (datif ek) ile eşleşiyordu.
    Artık kelime bazında ortak-önek karşılaştırması bu ek farkını tolere etmeli."""
    monkeypatch.setattr(matching, "geocode_district", lambda db, district: None)

    headers = _register(client, "Ofis Tip Test 3", "owner3@tip-test.com")
    client.post(
        "/listings",
        json={
            "title": "BEGO GAYRİMENKULDEN ULUYOLA YAKIN 600 M2 KİRALIK İŞ YERİ",
            "district": "Osmangazi",
            "price": 30000,
            "room_count": "Belirtilmedi",
            "listing_type": "rent",
            "property_type": "commercial",
        },
        headers=headers,
    )
    client.post(
        "/listings",
        json={
            "title": "Alakasız başka bir bölgede satılık daire",
            "district": "Nilüfer",
            "price": 900000,
            "room_count": "2+1",
        },
        headers=headers,
    )

    lead_resp = client.post(
        "/leads",
        json={
            "contact_phone": "5551114422",
            "district": "Uluyol Caddesi",
            "listing_type_preference": "rent",
            "property_type_preference": "commercial",
        },
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    titles = {m["title"] for m in match_resp.json()}
    assert titles == {"BEGO GAYRİMENKULDEN ULUYOLA YAKIN 600 M2 KİRALIK İŞ YERİ"}


def test_neighborhood_match_is_turkish_capital_i_safe(client, monkeypatch):
    """Regresyon: hem başlık hem aranan bölge Türkçe büyük "İ" içerdiğinde
    (ör. "İZMİR"), Python'un str.lower()'ının bunu bir COMBINING DOT ABOVE
    karakterine ayırması alt-dize aramasını kırmamalı (bkz. app/core/text.py)."""
    monkeypatch.setattr(matching, "geocode_district", lambda db, district: None)

    headers = _register(client, "Ofis Mahalle Test 3", "owner3@mahalle-test.com")
    client.post(
        "/listings",
        json={
            "title": "İZMİR KONAK'TA SATILIK DAİRE",
            "district": "Konak",
            "price": 900000,
            "room_count": "2+1",
        },
        headers=headers,
    )

    lead_resp = client.post(
        "/leads",
        json={"contact_phone": "5551113322", "district": "izmir", "room_count": "2+1"},
        headers=headers,
    )
    lead_id = lead_resp.json()["id"]

    match_resp = client.post(f"/leads/{lead_id}/match", headers=headers)
    assert match_resp.status_code == 200
    titles = {m["title"] for m in match_resp.json()}
    assert titles == {"İZMİR KONAK'TA SATILIK DAİRE"}
