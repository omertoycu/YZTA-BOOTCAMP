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
}


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
    )


def upload_photo(file_bytes: bytes, content_type: str, listing_id: str) -> str:
    """İlan fotoğrafını S3-uyumlu depoya yükler, herkese açık URL döner.

    s3_endpoint_url ayarlanmamışsa (henüz bucket kurulmadıysa) sert bir crash
    yerine anlamlı bir 503 döner — geri kalan uygulama fotoğrafsız çalışmaya devam eder.
    """
    if not settings.s3_endpoint_url or not settings.s3_bucket_name:
        raise HTTPException(status_code=503, detail="Fotoğraf yükleme şu an aktif değil")

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

    base = (settings.s3_public_url_base or settings.s3_endpoint_url).rstrip("/")
    return f"{base}/{settings.s3_bucket_name}/{key}"
