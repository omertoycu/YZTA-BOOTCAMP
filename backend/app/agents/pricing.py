import statistics

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.vectorstore import get_listings_collection
from app.models.listing import Listing

MIN_COMPARABLES_FOR_RANGE = 2


def _listing_document(listing: Listing) -> str:
    """Fiyatı BİLEREK içermez — embedding, ilanın konum/oda/metrekare
    karakteristiğini temsil etmeli, fiyatı değil (yoksa benzerlik araması
    fiyata göre kendi kendini doğrulayan bir döngüye döner)."""
    parts = [listing.district, listing.room_count]
    if listing.square_meters:
        parts.append(f"{listing.square_meters}m2")
    return " ".join(str(p) for p in parts)


def index_listing(listing: Listing) -> None:
    collection = get_listings_collection()
    collection.upsert(
        ids=[str(listing.id)],
        documents=[_listing_document(listing)],
        metadatas=[
            {
                "office_id": str(listing.office_id),
                "price": float(listing.price),
                "district": listing.district,
                "room_count": listing.room_count,
                "title": listing.title,
                "listing_type": listing.listing_type,
            }
        ],
    )


# Süreç ömrü boyunca zaten yeniden endekslenmiş ofisler — reindex her fiyat
# önerisi/durgun-portföy sorgusunda embedding hesaplamasın diye. ChromaDB'nin
# sıfırlanması yalnızca deploy'da (yani süreç yeniden başladığında) olur; set
# de aynı anda sıfırlandığı için "süreç başına bir kez" tam olarak doğru sıklık.
# İlan ekleme/silme/tip değişikliği zaten kendi endeks güncellemesini yapıyor.
_REINDEXED_OFFICE_IDS: set[str] = set()


def reindex_office_listings(db: Session) -> None:
    """Çağıran ofisin TÜM ilanlarını ChromaDB'ye TEK toplu upsert ile yeniden
    yazar — süreç başına ofis başına en fazla bir kez (bkz. _REINDEXED_OFFICE_IDS).

    Neden gerekli: Railway'de ChromaDB'nin kalıcı diski (Volume) yok — her
    deploy'da emsal endeksi sıfırlanıyor, index_listing ise sadece ilan
    OLUŞTURULURKEN çağrılıyordu. Sonuç: deploy'dan önce eklenmiş her ilan
    emsal havuzundan kayboluyor ve tüm fiyat önerileri "yeterli emsal yok"a
    düşüyordu (gerçek prod hatası, kullanıcı ekran görüntüsüyle bildirdi).

    İlk sürüm bunu HER sorguda ve ilan başına ayrı upsert'le yapıyordu — her
    dashboard/ilanlar sayfası yüklemesinde tüm portföy için embedding hesaplandı
    ve prod gözle görülür yavaşladı (kullanıcı bildirdi). Şimdi hem süreç başına
    bir kez hem tek toplu çağrı. Session RLS'li (get_tenant_db) olduğu için
    sadece çağıran ofisin ilanları görülür."""
    listings = db.execute(select(Listing)).scalars().all()
    if not listings:
        return
    office_id = str(listings[0].office_id)
    if office_id in _REINDEXED_OFFICE_IDS:
        return

    collection = get_listings_collection()
    collection.upsert(
        ids=[str(listing.id) for listing in listings],
        documents=[_listing_document(listing) for listing in listings],
        metadatas=[
            {
                "office_id": str(listing.office_id),
                "price": float(listing.price),
                "district": listing.district,
                "room_count": listing.room_count,
                "title": listing.title,
                "listing_type": listing.listing_type,
            }
            for listing in listings
        ],
    )
    _REINDEXED_OFFICE_IDS.add(office_id)


def remove_listing_from_index(listing_id) -> None:
    """İlan silindiğinde ChromaDB'deki emsal embedding'ini de temizler —
    aksi halde silinen bir ilan başka ilanların fiyat önerisinde hayalet
    emsal olarak kalmaya devam eder. Çağıran taraf (DELETE /listings/{id})
    bunu best-effort çağırır: burası patlarsa bile DB silme zaten tamamlanmış
    olur, stale bir embedding kalması sadece küçük bir veri kalitesi
    sorunudur, silme işlemini engellemez."""
    collection = get_listings_collection()
    collection.delete(ids=[str(listing_id)])


def suggest_price_range(listing: Listing, k: int = 5) -> dict:
    """Kesin bir AI fiyat tahmini DEĞİL — "benzer ilan aralığı" (bkz. Girişim
    Analizi Raporu Bölüm 2: savunulabilir, daha az riskli bir iddia).

    Emsaller, ChromaDB'de metadata filtresiyle sadece ARAYAN OFİSİN kendi
    portföyüne daraltılır — Postgres RLS ile tutarlı, tenant izolasyonunu
    vektör deposu üzerinden de korur. Pazar-geneli (cross-tenant) emsal
    verisi gelecek bir faz için değerlendirilebilir (bkz. TEKNIK_YOL_HARITASI.md).

    Ayrıca `listing_type` (satılık/kiralık) ile de daraltılır — aksi halde
    kiralık bir "2+1" (₺10.000'ler) ile satılık bir "2+1" (₺3.000.000'lar)
    aynı k-NN havuzuna girip anlamsız (hatta negatif) bir aralık üretiyordu
    (gerçek prod hatası, kullanıcı ekran görüntüsüyle bildirdi).
    """
    collection = get_listings_collection()
    results = collection.query(
        query_texts=[_listing_document(listing)],
        n_results=k + 1,  # +1: listing'in kendisi sonuçta çıkabilir
        where={
            "$and": [
                {"office_id": str(listing.office_id)},
                {"listing_type": listing.listing_type},
            ]
        },
    )

    ids = results["ids"][0] if results["ids"] else []
    metadatas = results["metadatas"][0] if results["metadatas"] else []

    comparables = [
        metadata for comp_id, metadata in zip(ids, metadatas) if comp_id != str(listing.id)
    ][:k]

    if len(comparables) < MIN_COMPARABLES_FOR_RANGE:
        return {
            "has_enough_data": False,
            "comparable_count": len(comparables),
            "message": (
                "Güvenilir bir aralık önermek için yeterli emsal ilan yok. "
                f"Bu bölgede/oda tipinde en az {MIN_COMPARABLES_FOR_RANGE} aktif ilan biriktikten "
                "sonra tekrar deneyin."
            ),
            "comparables": comparables,
        }

    prices = [comp["price"] for comp in comparables]
    mean_price = statistics.mean(prices)
    stdev_price = statistics.stdev(prices) if len(prices) > 1 else 0.0

    return {
        "has_enough_data": True,
        "comparable_count": len(comparables),
        "suggested_min": round(mean_price - stdev_price, 2),
        "suggested_max": round(mean_price + stdev_price, 2),
        "comparables": comparables,
    }
