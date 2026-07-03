"""FastAPI dependency providers."""
from app.config import Settings, get_settings
from app.models.face_detector import FaceDetector

def get_face_detector() -> FaceDetector:
    from app.main import face_detector
    return face_detector

def settings_dependency() -> Settings:
    return get_settings()
