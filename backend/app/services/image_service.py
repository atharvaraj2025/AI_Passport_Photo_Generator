"""Image loading, HEIC conversion, EXIF rotation, crop, background and save logic."""
from __future__ import annotations
from pathlib import Path
import cv2, numpy as np
from PIL import Image, ImageOps, ImageColor, UnidentifiedImageError
from loguru import logger
from app.config import Settings
from app.models.face_detector import FaceDetector, FaceBox
from app.schemas.passport import ProcessedPhoto
from app.utils.files import output_name

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception as exc:  # pragma: no cover
    logger.warning("HEIC support could not be registered: {}", exc)

class ImageProcessingError(Exception):
    """Domain-specific image processing failure."""
    def __init__(self, message: str, code: str = "image_processing_error") -> None:
        super().__init__(message)
        self.code = code

class PassportImageService:
    """Produces passport photos from user images."""
    def __init__(self, settings: Settings, detector: FaceDetector) -> None:
        self.settings = settings
        self.detector = detector

    def process_file(self, source: Path, original_filename: str, background_mode: str = "original", background_color: str | None = None) -> ProcessedPhoto:
        image = self._open_image(source)
        if background_mode == "solid":
            image = self._apply_solid_background(image, background_color or self.settings.solid_background_color)
        image_bgr = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
        faces = self.detector.detect(image_bgr)
        if not faces:
            raise ImageProcessingError("No face detected. Please use a clear front-facing photo.", "no_face")
        largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        cropped = self._passport_crop(image, largest)
        final = cropped.resize((self.settings.output_width, self.settings.output_height), Image.Resampling.LANCZOS).convert("RGB")
        out_name = output_name(original_filename)
        output_path = self._unique_output_path(out_name)
        final.save(output_path, "JPEG", quality=self.settings.jpeg_quality, optimize=True, progressive=True)
        logger.info("Processed {} -> {} ({} faces)", original_filename, output_path.name, len(faces))
        return ProcessedPhoto(
            original_filename=original_filename,
            output_filename=output_path.name,
            download_url=f"/api/download/{output_path.name}",
            width=self.settings.output_width,
            height=self.settings.output_height,
            faces_detected=len(faces),
            background_mode="solid" if background_mode == "solid" else "original",
        )

    def _open_image(self, source: Path) -> Image.Image:
        try:
            with Image.open(source) as img:
                return ImageOps.exif_transpose(img).convert("RGB")
        except UnidentifiedImageError as exc:
            raise ImageProcessingError("Image is corrupted or unsupported.", "corrupted_image") from exc
        except Exception as exc:
            raise ImageProcessingError(f"Unable to open image: {exc}", "image_open_failed") from exc

    def _passport_crop(self, image: Image.Image, face: FaceBox) -> Image.Image:
        w, h = image.size
        x1, y1, x2, y2 = face.bbox
        fw, fh = x2 - x1, y2 - y1
        cx = (x1 + x2) / 2
        # Bias downward to include forehead and shoulders while keeping face centered.
        top = y1 - 0.80 * fh
        bottom = y2 + 1.45 * fh
        crop_h = max(bottom - top, fh * 2.65)
        target_ratio = self.settings.output_width / self.settings.output_height
        crop_w = crop_h * target_ratio
        crop_w = max(crop_w, fw * 2.20)
        left = cx - crop_w / 2
        right = cx + crop_w / 2
        # Expand to boundaries without changing aspect ratio.
        if left < 0:
            right -= left; left = 0
        if right > w:
            left -= right - w; right = w
        if top < 0:
            bottom -= top; top = 0
        if bottom > h:
            top -= bottom - h; bottom = h
        left, top = max(0, left), max(0, top)
        right, bottom = min(w, right), min(h, bottom)
        # Final aspect correction around center.
        cw, ch = right - left, bottom - top
        current = cw / ch
        if current > target_ratio:
            new_w = ch * target_ratio; delta = (cw - new_w) / 2; left += delta; right -= delta
        else:
            new_h = cw / target_ratio; delta = (ch - new_h) / 2; top += delta; bottom -= delta
        return image.crop((round(left), round(top), round(right), round(bottom)))

    def _apply_solid_background(self, image: Image.Image, color: str) -> Image.Image:
        rgb = ImageColor.getrgb(color)
        if image.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", image.size, rgb)
            bg.paste(image, mask=image.getchannel("A"))
            return bg
        return Image.blend(Image.new("RGB", image.size, rgb), image.convert("RGB"), 0.92)

    def _unique_output_path(self, filename: str) -> Path:
        base = self.settings.output_dir / filename
        if not base.exists():
            return base
        stem, suffix = base.stem, base.suffix
        i = 1
        while True:
            candidate = self.settings.output_dir / f"{stem}_{i}{suffix}"
            if not candidate.exists():
                return candidate
            i += 1
