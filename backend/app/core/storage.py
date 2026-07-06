import uuid

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException

from app.core.config import settings

CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    # Sahibinden'in görsel CDN'i (i0.shbdn.com) bazı fotoğrafları avif olarak
    # sunuyor (curl ile doğrulandı) — bulk aktarımda kapak fotoğrafı çekimi
    # bu format için de çalışmalı.
    "image/avif": "avif",
}

MAX_PHOTO_BYTES = 8 * 1024 * 1024  # 8MB


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
    )


def upload_photo(file_bytes: bytes, content_type: str, listing_id: str) -> str:
    """İlan fotoğrafını S3-uyumlu depoya yükler, saklanacak nesne anahtarını (key) döner.

    Railway Buckets (Tigris altyapılı) public bucket desteklemiyor — ACL="public-read"
    göndersek de bucket private kalıyor ve doğrudan URL'ler tarayıcıda 403 verir
    (bkz. GET /listings/photos/{key} proxy route'u). Bu yüzden burada URL değil,
    sadece object key üretilip döndürülüyor; herkese açık URL'e çevirme işi
    photo_proxy_url()'e bırakılıyor.

    s3_endpoint_url ayarlanmamışsa (henüz bucket kurulmadıysa) sert bir crash
    yerine anlamlı bir 503 döner — geri kalan uygulama fotoğrafsız çalışmaya devam eder.
    """
    if not settings.s3_endpoint_url or not settings.s3_bucket_name:
        raise HTTPException(status_code=503, detail="Fotoğraf yükleme şu an aktif değil")

    if len(file_bytes) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Fotoğraf çok büyük (maksimum 8MB)")

    extension = CONTENT_TYPE_EXTENSIONS.get(content_type)
    if not extension:
        raise HTTPException(status_code=422, detail="Desteklenmeyen dosya türü (jpg/png/webp/gif olmalı)")

    key = f"listings/{listing_id}/{uuid.uuid4()}.{extension}"

    try:
        client = _get_s3_client()
        client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=502, detail="Fotoğraf yüklenemedi, tekrar deneyin") from exc

    return key


def upload_office_logo(file_bytes: bytes, content_type: str, office_id: str) -> str:
    """Ofis logosunu yükler, saklanacak nesne anahtarını döner — upload_photo
    ile aynı kurallar (boyut sınırı, tip whitelist'i, private bucket), sadece
    anahtar öneki farklı: offices/{office_id}/logo-{uuid}.{ext}."""
    if not settings.s3_endpoint_url or not settings.s3_bucket_name:
        raise HTTPException(status_code=503, detail="Logo yükleme şu an aktif değil")

    if len(file_bytes) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Logo çok büyük (maksimum 8MB)")

    extension = CONTENT_TYPE_EXTENSIONS.get(content_type)
    if not extension:
        raise HTTPException(status_code=422, detail="Desteklenmeyen dosya türü (jpg/png/webp/gif olmalı)")

    key = f"offices/{office_id}/logo-{uuid.uuid4()}.{extension}"

    try:
        client = _get_s3_client()
        client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=502, detail="Logo yüklenemedi, tekrar deneyin") from exc

    return key


def logo_proxy_url(logo_key: str | None) -> str | None:
    """offices.logo_key'i GET /offices/logo/{key} proxy route'una işaret eden
    URL'e çevirir (photo_proxy_url ile aynı desen — bucket private olduğu
    için doğrudan S3 URL'i tarayıcıda 403 verir)."""
    if not logo_key:
        return None
    base = settings.public_base_url.rstrip("/")
    return f"{base}/offices/logo/{logo_key}"


def fetch_photo(key: str) -> tuple[bytes, str]:
    """Bir fotoğrafı bucket'tan backend credential'ıyla çekip bayt+content-type döner.

    GET /listings/photos/{key} route'u bunu kullanarak private bucket'taki dosyayı
    tarayıcıya akıtır (proxy) — bucket seviyesinde public erişim olmadığı için tek yol bu.
    """
    if not settings.s3_endpoint_url or not settings.s3_bucket_name:
        raise HTTPException(status_code=503, detail="Fotoğraf deposu şu an aktif değil")

    try:
        client = _get_s3_client()
        obj = client.get_object(Bucket=settings.s3_bucket_name, Key=key)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in ("NoSuchKey", "404"):
            raise HTTPException(status_code=404, detail="Fotoğraf bulunamadı") from exc
        raise HTTPException(status_code=502, detail="Fotoğraf alınamadı") from exc
    except BotoCoreError as exc:
        raise HTTPException(status_code=502, detail="Fotoğraf alınamadı") from exc

    body = obj["Body"].read()
    content_type = obj.get("ContentType") or "application/octet-stream"
    return body, content_type


def photo_proxy_url(stored_value: str) -> str:
    """Listing.photos'ta saklanan değeri (yeni: bare S3 key, eski: bucket public
    olduğu varsayımıyla kaydedilmiş tam URL) her zaman backend proxy route'una
    işaret eden sabit bir URL'e çevirir. Anahtar formatı her zaman
    'listings/{listing_id}/{uuid}.{ext}' olduğundan eski tam URL'lerden de
    bu kısmı ayıklamak yeterli."""
    marker = "listings/"
    idx = stored_value.find(marker)
    key = stored_value[idx:] if idx != -1 else stored_value
    base = settings.public_base_url.rstrip("/")
    return f"{base}/listings/photos/{key}"
