"""FastAPI entry point for AI Passport Photo Generator."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from app.api.passport import router as passport_router
from app.config import get_settings
from app.models.face_detector import FaceDetector
from app.schemas.passport import HealthResponse
from app.utils.logging import configure_logging

settings = get_settings()
configure_logging(settings)
face_detector = FaceDetector(settings.insightface_model, settings.insightface_providers)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting {} {}", settings.app_name, settings.app_version)
    face_detector.load()
    yield
    logger.info("Shutting down {}", settings.app_name)

app = FastAPI(title=settings.app_name, version=settings.app_version, description="Local AI passport photo generator with InsightFace detection only.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(passport_router)

@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error at {}", request.url.path)
    return JSONResponse(status_code=500, content={"message": "Unexpected server error", "detail": str(exc), "code": "server_error"})

@app.get("/")
async def root() -> dict[str, str]:
    return {"app": settings.app_name, "docs": "/docs", "health": "/health"}

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name, version=settings.app_version, model_loaded=face_detector.loaded)
