"""High-level orchestration for single, multiple and ZIP processing."""
from __future__ import annotations
import shutil, time, zipfile
from pathlib import Path
from fastapi import UploadFile
from loguru import logger
from app.config import Settings
from app.models.face_detector import FaceDetector
from app.models.background_remover import BackgroundRemover
from app.schemas.passport import ProcessingSummary, ErrorDetail, ProcessedPhoto
from app.services.image_service import PassportImageService, ImageProcessingError
from app.utils.files import safe_filename, save_upload, validate_extension, extract_zip

class PassportService:
    def __init__(self, settings: Settings, detector: FaceDetector, background_remover: BackgroundRemover) -> None:
        self.settings = settings
        self.image_service = PassportImageService(settings, detector, background_remover)

    async def process_uploads(self, files: list[UploadFile], background_mode: str, background_color: str | None) -> ProcessingSummary:
        if not files:
            raise ValueError("No files were uploaded")
        if len(files) > self.settings.max_images:
            raise ValueError(f"Maximum {self.settings.max_images} images are allowed")
        start = time.perf_counter(); results=[]; errors=[]
        for file in files:
            filename = safe_filename(file.filename or "upload")
            try:
                validate_extension(filename, self.settings, allow_zip=False)
                path = await save_upload(file, self.settings.upload_dir / filename, self.settings.max_image_bytes)
                results.append(self.image_service.process_file(path, filename, background_mode, background_color))
            except Exception as exc:
                code = getattr(exc, "code", "validation_error")
                errors.append(ErrorDetail(filename=filename, message=str(exc), code=code))
                logger.exception("Failed processing {}", filename)
        return ProcessingSummary(total=len(files), successful=len(results), failed=len(errors), elapsed_seconds=round(time.perf_counter()-start, 2), results=results, errors=errors)

    async def process_zip(self, file: UploadFile, background_mode: str, background_color: str | None) -> ProcessingSummary:
        filename = safe_filename(file.filename or "archive.zip")
        validate_extension(filename, self.settings, allow_zip=True)
        if not filename.lower().endswith(".zip"):
            raise ValueError("ZIP endpoint accepts only .zip files")
        start = time.perf_counter(); extract_dir = self.settings.temp_dir / f"extract_{int(start*1000)}"
        extract_dir.mkdir(parents=True, exist_ok=True)
        try:
            zip_path = await save_upload(file, self.settings.upload_dir / filename, self.settings.max_zip_bytes)
            paths = extract_zip(zip_path, extract_dir, self.settings)
            results: list[ProcessedPhoto] = []; errors: list[ErrorDetail] = []
            for path in paths:
                if path.stat().st_size > self.settings.max_image_bytes:
                    errors.append(ErrorDetail(filename=path.name, message="Image exceeds size limit", code="file_too_large")); continue
                try:
                    results.append(self.image_service.process_file(path, path.name, background_mode, background_color))
                except ImageProcessingError as exc:
                    errors.append(ErrorDetail(filename=path.name, message=str(exc), code=exc.code))
            return ProcessingSummary(total=len(paths), successful=len(results), failed=len(errors), elapsed_seconds=round(time.perf_counter()-start, 2), results=results, errors=errors)
        finally:
            shutil.rmtree(extract_dir, ignore_errors=True)

    def create_all_zip(self) -> Path:
        zip_path = self.settings.output_dir / "passport_photos.zip"
        images = sorted(p for p in self.settings.output_dir.glob("*.jpg") if p.name != zip_path.name)
        if not images:
            raise FileNotFoundError("No processed photos are available")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for image in images:
                archive.write(image, image.name)
        return zip_path

    def cleanup(self) -> dict[str, int]:
        counts = {"uploads": 0, "outputs": 0, "temp": 0}
        for key, folder in (("uploads", self.settings.upload_dir), ("outputs", self.settings.output_dir), ("temp", self.settings.temp_dir)):
            for path in folder.iterdir():
                if path.is_file(): path.unlink(); counts[key] += 1
                elif path.is_dir(): shutil.rmtree(path); counts[key] += 1
        return counts
