"""Passport photo API routes."""
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from loguru import logger
from app.config import Settings, get_settings
from app.dependencies import get_background_remover, get_face_detector
from app.models.face_detector import FaceDetector
from app.models.background_remover import BackgroundRemover
from app.schemas.passport import ProcessingSummary
from app.services.passport_service import PassportService

router = APIRouter(prefix="/api", tags=["passport"])

def service(
    settings: Settings = Depends(get_settings),
    detector: FaceDetector = Depends(get_face_detector),
    background_remover: BackgroundRemover = Depends(get_background_remover),
) -> PassportService:
    return PassportService(settings, detector, background_remover)

@router.post("/passport/single", response_model=ProcessingSummary)
async def process_single(file: UploadFile = File(...), background_mode: str = Form("original"), background_color: str | None = Form(None), svc: PassportService = Depends(service)) -> ProcessingSummary:
    logger.info("Single upload: {}", file.filename)
    return await svc.process_uploads([file], background_mode, background_color)

@router.post("/passport/multiple", response_model=ProcessingSummary)
async def process_multiple(files: list[UploadFile] = File(...), background_mode: str = Form("original"), background_color: str | None = Form(None), svc: PassportService = Depends(service)) -> ProcessingSummary:
    logger.info("Multiple upload count: {}", len(files))
    return await svc.process_uploads(files, background_mode, background_color)

@router.post("/passport/zip", response_model=ProcessingSummary)
async def process_zip(file: UploadFile = File(...), background_mode: str = Form("original"), background_color: str | None = Form(None), svc: PassportService = Depends(service)) -> ProcessingSummary:
    logger.info("ZIP upload: {}", file.filename)
    return await svc.process_zip(file, background_mode, background_color)

@router.get("/download/{filename}")
async def download_file(filename: str, settings: Settings = Depends(get_settings)) -> FileResponse:
    safe = Path(filename).name
    path = settings.output_dir / safe
    if not path.exists() or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"message": "File not found"})
    logger.info("Download: {}", safe)
    return FileResponse(path, media_type="image/jpeg", filename=safe)

@router.get("/download/all")
async def download_all(svc: PassportService = Depends(service)) -> FileResponse:
    path = svc.create_all_zip()
    logger.info("Batch ZIP download: {}", path)
    return FileResponse(path, media_type="application/zip", filename="passport_photos.zip")

@router.delete("/cleanup")
async def cleanup(svc: PassportService = Depends(service)) -> dict[str, object]:
    counts = svc.cleanup()
    logger.warning("Cleanup completed: {}", counts)
    return {"message": "Cleanup completed", "deleted": counts}
