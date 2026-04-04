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


def media_root_path() -> Path:
    path = Path(settings.MEDIA_ROOT)
    path.mkdir(parents=True, exist_ok=True)
    return path


def organization_logo_directory(organization_id: UUID | str) -> Path:
    path = media_root_path() / settings.ORGANIZATION_LOGO_DIR / str(organization_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


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
    directory = organization_logo_directory(organization_id)
    filename = f"{uuid4().hex}{extension}"
    file_path = directory / filename
    file_path.write_bytes(content)

    return f"{settings.MEDIA_URL_PREFIX}/{settings.ORGANIZATION_LOGO_DIR}/{organization_id}/{filename}"


def delete_managed_logo(logo_url: str | None) -> None:
    if not logo_url:
        return

    prefix = f"{settings.MEDIA_URL_PREFIX}/{settings.ORGANIZATION_LOGO_DIR}/"
    if not logo_url.startswith(prefix):
        return

    relative_path = logo_url.removeprefix(f"{settings.MEDIA_URL_PREFIX}/")
    file_path = media_root_path() / relative_path
    if file_path.exists():
        file_path.unlink()
