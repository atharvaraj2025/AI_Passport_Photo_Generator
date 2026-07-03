"""Local AI background removal using RMBG-2.0/BiRefNet style matting models."""
from __future__ import annotations

from threading import Lock
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from loguru import logger
from PIL import Image, ImageFilter

from app.config import Settings


class BackgroundRemovalError(RuntimeError):
    """Raised when the local segmentation model cannot produce an alpha matte."""


class BackgroundRemover:
    """Reusable local portrait/background segmentation model.

    The model is loaded lazily once, moved to CUDA when available, and reused for
    all FastAPI requests. ``remove`` returns the original image content with an
    AI-generated alpha channel, leaving crop/resize/background-color decisions to
    the passport service.
    """

    def __init__(self, settings: Settings) -> None:
        self.model_id = settings.background_removal_model
        self.input_size = settings.background_removal_input_size
        self.max_side = settings.background_removal_max_side
        self.alpha_feather_radius = settings.background_alpha_feather_radius
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model: Any | None = None
        self._processor: Any | None = None
        self._lock = Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        """Load the segmentation model once for the current process."""
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            try:
                from transformers import AutoModelForImageSegmentation, AutoProcessor

                logger.info("Loading background removal model {} on {}", self.model_id, self.device)
                try:
                    self._processor = AutoProcessor.from_pretrained(self.model_id, trust_remote_code=True)
                except Exception as exc:  # Some RMBG checkpoints do not ship a processor.
                    logger.debug("No AutoProcessor available for {}: {}", self.model_id, exc)
                    self._processor = None

                model = AutoModelForImageSegmentation.from_pretrained(self.model_id, trust_remote_code=True)
                model.to(self.device)
                model.eval()
                self._model = model
                logger.info("Background removal model loaded")
            except Exception as exc:  # pragma: no cover - depends on local model installation.
                raise BackgroundRemovalError(f"Unable to load background removal model '{self.model_id}': {exc}") from exc

    def remove(self, image: Image.Image) -> Image.Image:
        """Return an RGBA copy of ``image`` with the background made transparent."""
        self.load()
        rgb = image.convert("RGB")
        inference_image, scale = self._resize_for_inference(rgb)
        try:
            alpha = self._predict_alpha(inference_image)
        except torch.cuda.OutOfMemoryError as exc:  # pragma: no cover - hardware dependent.
            if self.device.type == "cuda":
                torch.cuda.empty_cache()
            raise BackgroundRemovalError("GPU ran out of memory while removing the background") from exc
        except Exception as exc:
            raise BackgroundRemovalError(f"Background removal failed: {exc}") from exc
        finally:
            if self.device.type == "cuda":
                torch.cuda.empty_cache()

        if scale != 1.0:
            alpha = alpha.resize(rgb.size, Image.Resampling.LANCZOS)
        alpha = self._refine_alpha(alpha)
        rgba = rgb.convert("RGBA")
        rgba.putalpha(alpha)
        return rgba

    def _resize_for_inference(self, image: Image.Image) -> tuple[Image.Image, float]:
        width, height = image.size
        longest = max(width, height)
        if longest <= self.max_side:
            return image, 1.0
        scale = self.max_side / float(longest)
        size = (max(1, round(width * scale)), max(1, round(height * scale)))
        return image.resize(size, Image.Resampling.LANCZOS), scale

    def _predict_alpha(self, image: Image.Image) -> Image.Image:
        assert self._model is not None
        with torch.no_grad():
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=self.device.type == "cuda"):
                if self._processor is not None:
                    inputs = self._processor(images=image, return_tensors="pt")
                    inputs = {key: value.to(self.device) for key, value in inputs.items()}
                    output = self._model(**inputs)
                else:
                    output = self._model(self._manual_tensor(image))

        mask = self._extract_mask_tensor(output)
        mask = F.interpolate(mask, size=(image.height, image.width), mode="bilinear", align_corners=False)
        mask = mask.squeeze().detach().float().cpu().clamp(0, 1).numpy()
        return Image.fromarray((mask * 255).astype(np.uint8), mode="L")

    def _manual_tensor(self, image: Image.Image) -> torch.Tensor:
        resized = image.resize((self.input_size, self.input_size), Image.Resampling.BICUBIC)
        array = np.asarray(resized).astype(np.float32) / 255.0
        tensor = torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0)
        mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
        return ((tensor - mean) / std).to(self.device)

    def _extract_mask_tensor(self, output: Any) -> torch.Tensor:
        if hasattr(output, "logits"):
            mask = output.logits
        elif isinstance(output, dict):
            mask = output.get("logits")
            if mask is None:
                mask = output.get("out")
            if mask is None:
                mask = output.get("pred")
        elif isinstance(output, (list, tuple)):
            mask = output[-1]
            if isinstance(mask, (list, tuple)):
                mask = mask[-1]
        else:
            mask = output
        if not torch.is_tensor(mask):
            raise BackgroundRemovalError("Segmentation model returned an unsupported output type")
        if mask.ndim == 3:
            mask = mask.unsqueeze(1)
        if mask.shape[1] != 1:
            mask = mask[:, :1]
        return mask.sigmoid() if mask.min() < 0 or mask.max() > 1 else mask

    def _refine_alpha(self, alpha: Image.Image) -> Image.Image:
        if self.alpha_feather_radius > 0:
            alpha = alpha.filter(ImageFilter.GaussianBlur(radius=self.alpha_feather_radius))
        return alpha
