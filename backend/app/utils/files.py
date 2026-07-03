"""File validation and naming helpers."""
from __future__ import annotations
import re, shutil, zipfile
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from app.config import Settings

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")

def safe_filename(filename: str) -> str:
    name = Path(filename).name.strip().replace(" ", "_")
    cleaned = _SAFE.sub("", name)
    return cleaned or "upload"

def output_name(original: str) -> str:
    stem = Path(safe_filename(original)).stem
    return f"{stem}_passport.jpg"

def validate_extension(filename: str, settings: Settings, allow_zip: bool = True) -> str:
    ext = Path(filename).suffix.lower()
    allowed = settings.allowed_extensions if allow_zip else settings.allowed_image_extensions
    if ext not in allowed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"message": f"Unsupported file type '{ext or 'none'}' for {filename}"})
    return ext

async def save_upload(file: UploadFile, destination: Path, max_bytes: int) -> Path:
    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"message": "Empty upload filename"})
    destination.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with destination.open("wb") as handle:
        while chunk := await file.read(1024 * 1024):
            total += len(chunk)
            if total > max_bytes:
                destination.unlink(missing_ok=True)
                raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail={"message": f"File {file.filename} exceeds size limit"})
            handle.write(chunk)
    if total == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"message": f"File {file.filename} is empty"})
    await file.seek(0)
    return destination

def extract_zip(zip_path: Path, target_dir: Path, settings: Settings) -> list[Path]:
    try:
        with zipfile.ZipFile(zip_path) as archive:
            if archive.testzip() is not None:
                raise ValueError("ZIP archive contains corrupted entries")
            paths: list[Path] = []
            for member in archive.infolist():
                p = Path(member.filename)
                if member.is_dir() or any(part.startswith(".") for part in p.parts):
                    continue
                if p.suffix.lower() not in settings.allowed_image_extensions:
                    continue
                if len(paths) >= settings.max_images:
                    break
                dest = target_dir / safe_filename(p.name)
                with archive.open(member) as source, dest.open("wb") as out:
                    shutil.copyfileobj(source, out)
                paths.append(dest)
            if not paths:
                raise ValueError("ZIP archive does not contain supported images")
            return paths
    except zipfile.BadZipFile as exc:
        raise ValueError("Invalid ZIP archive") from exc
