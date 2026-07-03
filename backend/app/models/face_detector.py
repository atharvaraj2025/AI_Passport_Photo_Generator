"""InsightFace face detection wrapper loaded once at startup."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from loguru import logger

@dataclass(frozen=True)
class FaceBox:
    bbox: tuple[float, float, float, float]
    det_score: float

class FaceDetector:
    """Thin wrapper around InsightFace FaceAnalysis for detection only."""
    def __init__(self, model_name: str, providers: list[str]) -> None:
        self.model_name = model_name
        self.providers = providers
        self._app = None

    def load(self) -> None:
        if self._app is not None:
            return
        from insightface.app import FaceAnalysis
        logger.info("Loading InsightFace detection model: {}", self.model_name)
        app = FaceAnalysis(name=self.model_name, providers=self.providers, allowed_modules=["detection"])
        app.prepare(ctx_id=0, det_size=(640, 640))
        self._app = app
        logger.info("InsightFace model loaded")

    @property
    def loaded(self) -> bool:
        return self._app is not None

    def detect(self, image_bgr: np.ndarray) -> list[FaceBox]:
        if self._app is None:
            raise RuntimeError("Face detector has not been loaded")
        faces = self._app.get(image_bgr)
        return [FaceBox(tuple(map(float, face.bbox)), float(getattr(face, "det_score", 0.0))) for face in faces]
