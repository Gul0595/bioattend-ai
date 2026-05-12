"""
BioAttend Ultimate — Storage Service
Supports local filesystem, AWS S3, and MinIO.
"""
from __future__ import annotations

import base64
import io
import uuid
from pathlib import Path
from typing import Optional

from app.core.config import settings


def _get_s3_client():
    import boto3
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def _get_minio_client():
    from minio import Minio
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=False,
    )


def upload_image(image_bytes: bytes, folder: str = "uploads") -> str:
    """Upload image bytes and return a public-accessible URL."""
    filename = f"{folder}/{uuid.uuid4().hex}.jpg"

    if settings.STORAGE_BACKEND == "s3":
        client = _get_s3_client()
        client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=filename,
            Body=image_bytes,
            ContentType="image/jpeg",
        )
        return f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{filename}"

    elif settings.STORAGE_BACKEND == "minio":
        client = _get_minio_client()
        client.put_object(
            settings.MINIO_BUCKET,
            filename,
            io.BytesIO(image_bytes),
            length=len(image_bytes),
            content_type="image/jpeg",
        )
        return f"http://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{filename}"

    else:  # local
        path = Path(settings.LOCAL_STORAGE_PATH) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image_bytes)
        return f"/storage/{filename}"


def base64_to_bytes(b64_str: str) -> bytes:
    if "," in b64_str:
        b64_str = b64_str.split(",")[1]
    return base64.b64decode(b64_str)


def ensure_storage_dirs() -> None:
    if settings.STORAGE_BACKEND == "local":
        for folder in ("faces", "checkins", "reports"):
            (Path(settings.LOCAL_STORAGE_PATH) / folder).mkdir(parents=True, exist_ok=True)
