from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/octet-stream",
}
MAX_UPLOAD_BYTES = settings.max_upload_mb * 1024 * 1024


def _detect_extension(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def _friendly_error(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


async def save_image_upload(file: UploadFile | None, folder: str) -> str:
    if file is None or not file.filename:
        raise _friendly_error("Please choose an image file")

    original = Path(file.filename)
    extension = original.suffix.lower().lstrip(".")
    if extension not in ALLOWED_EXTENSIONS:
        raise _friendly_error("Only JPG, PNG, GIF, and WEBP images are allowed")
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise _friendly_error("The uploaded file is not a supported image")

    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if not data:
        raise _friendly_error("The uploaded image is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise _friendly_error(f"Image must be smaller than {settings.max_upload_mb} MB")

    detected = _detect_extension(data)
    if detected is None:
        raise _friendly_error("The file content is not a valid image")
    if detected == "jpg":
        detected_extensions = {"jpg", "jpeg"}
    else:
        detected_extensions = {detected}
    if extension not in detected_extensions:
        raise _friendly_error("The file extension does not match the image content")

    import uuid

    filename = f"{uuid.uuid4().hex}.{detected}"
    target_dir = settings.upload_path / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename

    await run_in_threadpool(target.write_bytes, data)
    return f"/uploads/{folder}/{filename}"


def delete_image_file(public_path: str | None) -> None:
    if not public_path or not public_path.startswith("/uploads/"):
        return
    relative = public_path.removeprefix("/uploads/")
    target = (settings.upload_path / relative).resolve()
    upload_root = settings.upload_path.resolve()
    if upload_root not in target.parents and target != upload_root:
        return
    try:
        if target.is_file():
            target.unlink()
    except OSError:
        pass
