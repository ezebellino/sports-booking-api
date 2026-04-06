from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile

from app.core.config import settings

ALLOWED_LOGO_MIME_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}


def is_local_media_storage() -> bool:
    return settings.MEDIA_STORAGE_BACKEND.lower() == "local"


def media_root_path() -> Path:
    path = Path(settings.MEDIA_ROOT)
    path.mkdir(parents=True, exist_ok=True)
    return path


def organization_logo_directory(organization_id: UUID | str) -> Path:
    path = media_root_path() / settings.ORGANIZATION_LOGO_DIR / str(organization_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def normalize_s3_key_prefix() -> str:
    return settings.S3_KEY_PREFIX.strip().strip("/")


def build_storage_key(*parts: str) -> str:
    key_parts = [part.strip("/") for part in parts if part]
    prefix = normalize_s3_key_prefix()
    if prefix:
        key_parts.insert(0, prefix)
    return "/".join(key_parts)


def get_s3_client():
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("Falta instalar boto3 para usar MEDIA_STORAGE_BACKEND=s3.") from exc

    return boto3.client(
        "s3",
        region_name=settings.S3_REGION or None,
        endpoint_url=settings.S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
    )


def require_s3_configuration() -> None:
    missing = []
    if not settings.S3_BUCKET_NAME:
        missing.append("S3_BUCKET_NAME")
    if not settings.S3_PUBLIC_BASE_URL:
        missing.append("S3_PUBLIC_BASE_URL")
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Falta configurar storage externo: {', '.join(missing)}.",
        )


def build_public_s3_url(storage_key: str) -> str:
    base_url = (settings.S3_PUBLIC_BASE_URL or "").rstrip("/")
    return f"{base_url}/{storage_key}"


async def save_uploaded_logo(file: UploadFile, organization_id: UUID | str) -> str:
    if file.content_type not in ALLOWED_LOGO_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Formato de logo no permitido. Usa PNG, JPG, WEBP o SVG.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo de logo esta vacio.")

    if len(content) > settings.MAX_LOGO_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="El logo supera el tamano maximo permitido.")

    extension = ALLOWED_LOGO_MIME_TYPES[file.content_type]
    filename = f"{uuid4().hex}{extension}"

    if is_local_media_storage():
        directory = organization_logo_directory(organization_id)
        file_path = directory / filename
        file_path.write_bytes(content)
        return f"{settings.MEDIA_URL_PREFIX}/{settings.ORGANIZATION_LOGO_DIR}/{organization_id}/{filename}"

    require_s3_configuration()
    storage_key = build_storage_key(settings.ORGANIZATION_LOGO_DIR, str(organization_id), filename)
    try:
        get_s3_client().put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=storage_key,
            Body=content,
            ContentType=file.content_type,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="No pudimos guardar el logo en storage externo.") from exc

    return build_public_s3_url(storage_key)


def delete_managed_logo(logo_url: str | None) -> None:
    if not logo_url:
        return

    if is_local_media_storage():
        prefix = f"{settings.MEDIA_URL_PREFIX}/{settings.ORGANIZATION_LOGO_DIR}/"
        if not logo_url.startswith(prefix):
            return

        relative_path = logo_url.removeprefix(f"{settings.MEDIA_URL_PREFIX}/")
        file_path = media_root_path() / relative_path
        if file_path.exists():
            file_path.unlink()
        return

    base_url = (settings.S3_PUBLIC_BASE_URL or "").rstrip("/")
    if not base_url:
        return
    expected_prefix = f"{base_url}/"
    if not logo_url.startswith(expected_prefix):
        return

    storage_key = logo_url.removeprefix(expected_prefix)
    try:
        get_s3_client().delete_object(Bucket=settings.S3_BUCKET_NAME, Key=storage_key)
    except Exception:
        return
