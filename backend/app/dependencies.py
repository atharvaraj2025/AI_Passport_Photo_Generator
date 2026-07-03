"""FastAPI dependency providers."""
from app.config import Settings, get_settings
from app.models.face_detector import FaceDetector
from app.models.background_remover import BackgroundRemover

def get_face_detector() -> FaceDetector:
    from app.main import face_detector
    return face_detector

def get_background_remover() -> BackgroundRemover:
    from app.main import background_remover
    return background_remover

def settings_dependency() -> Settings:
    return get_settings()
