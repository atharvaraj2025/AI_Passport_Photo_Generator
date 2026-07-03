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
        image_bgr = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
        faces = self.detector.detect(image_bgr)
        if not faces:
            raise ImageProcessingError("No face detected. Please use a clear front-facing photo.", "no_face")
        largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        cropped, cropped_face = self._passport_crop(image, largest)
        if background_mode == "solid":
            cropped = self._apply_solid_background(
                cropped,
                background_color or self.settings.solid_background_color,
                cropped_face,
            )
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

    def _passport_crop(self, image: Image.Image, face: FaceBox) -> tuple[Image.Image, FaceBox]:
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
        crop_box = (round(left), round(top), round(right), round(bottom))
        cropped_face = FaceBox(
            bbox=(
                face.bbox[0] - crop_box[0],
                face.bbox[1] - crop_box[1],
                face.bbox[2] - crop_box[0],
                face.bbox[3] - crop_box[1],
            ),
            det_score=face.det_score,
        )
        return image.crop(crop_box), cropped_face

    def _apply_solid_background(self, image: Image.Image, color: str, face: FaceBox) -> Image.Image:
        rgb = ImageColor.getrgb(color)
        rgb_image = image.convert("RGB")
        if image.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", image.size, rgb)
            bg.paste(image, mask=image.getchannel("A"))
            return bg

        # Replace only the estimated background. The previous implementation
        # blended the selected color over the whole image, which left the
        # original background visible and made the UI option appear broken.
        mask = self._foreground_mask(rgb_image, face)
        background = Image.new("RGB", rgb_image.size, rgb)
        return Image.composite(rgb_image, background, Image.fromarray(mask, mode="L"))

    def _foreground_mask(self, image: Image.Image, face: FaceBox) -> np.ndarray:
        width, height = image.size
        x1, y1, x2, y2 = face.bbox
        fw, fh = max(1.0, x2 - x1), max(1.0, y2 - y1)
        cx = (x1 + x2) / 2

        # Start from probable background everywhere and explicitly seed only
        # the portrait area as foreground. Marking a large rectangle as probable
        # foreground keeps doors/walls behind the person, which is why only
        # part of the background changed in real user photos.
        mask = np.full((height, width), cv2.GC_PR_BGD, dtype=np.uint8)
        border = max(6, min(width, height) // 35)
        mask[:border, :] = cv2.GC_BGD
        mask[-border:, :] = cv2.GC_BGD
        mask[:, :border] = cv2.GC_BGD
        mask[:, -border:] = cv2.GC_BGD

        # Also mark pixels that look like the outer-edge background as definite
        # background. This removes interior wall/door regions that are not
        # connected to the crop edge after the passport crop.
        rgb = np.array(image)
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        edge_pixels = np.concatenate(
            (
                lab[:border, :, :].reshape(-1, 3),
                lab[-border:, :, :].reshape(-1, 3),
                lab[:, :border, :].reshape(-1, 3),
                lab[:, -border:, :].reshape(-1, 3),
            ),
            axis=0,
        )
        edge_mean = edge_pixels.mean(axis=0)
        distance = np.linalg.norm(lab.astype(np.float32) - edge_mean.astype(np.float32), axis=2)
        mask[distance < 28] = cv2.GC_BGD

        # Face/head is definite foreground.
        head_center = (int(cx), int(y1 + fh * 0.45))
        head_axes = (max(2, int(fw * 0.78)), max(2, int(fh * 0.95)))
        cv2.ellipse(mask, head_center, head_axes, 0, 0, 360, cv2.GC_FGD, -1)

        # Hair/upper body and shoulders are probable foreground, but the rest of
        # the crop remains background so GrabCut can remove all visible scenery.
        upper_top = max(0, int(y1 - fh * 0.25))
        upper_bottom = min(height - 1, int(y2 + fh * 0.55))
        upper_left = max(0, int(cx - fw * 1.05))
        upper_right = min(width - 1, int(cx + fw * 1.05))
        upper_region = mask[upper_top:upper_bottom, upper_left:upper_right]
        upper_region[upper_region == cv2.GC_PR_BGD] = cv2.GC_PR_FGD

        shoulders_y = min(height - 1, int(y2 + fh * 0.65))
        body_bottom = height - 1
        body = np.array(
            [
                [max(0, int(cx - fw * 1.25)), shoulders_y],
                [min(width - 1, int(cx + fw * 1.25)), shoulders_y],
                [min(width - 1, int(cx + fw * 2.05)), body_bottom],
                [max(0, int(cx - fw * 2.05)), body_bottom],
            ],
            dtype=np.int32,
        )
        cv2.fillPoly(mask, [body], cv2.GC_PR_FGD)

        # A smaller torso core is definite foreground so striped/dark clothing is
        # not accidentally removed when it differs strongly from the face.
        torso = np.array(
            [
                [max(0, int(cx - fw * 0.75)), min(height - 1, int(y2 + fh * 0.75))],
                [min(width - 1, int(cx + fw * 0.75)), min(height - 1, int(y2 + fh * 0.75))],
                [min(width - 1, int(cx + fw * 1.15)), body_bottom],
                [max(0, int(cx - fw * 1.15)), body_bottom],
            ],
            dtype=np.int32,
        )
        cv2.fillPoly(mask, [torso], cv2.GC_FGD)
        mask[:border, :] = cv2.GC_BGD
        mask[-border:, :] = cv2.GC_BGD
        mask[:, :border] = cv2.GC_BGD
        mask[:, -border:] = cv2.GC_BGD

        image_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        bg_model = np.zeros((1, 65), np.float64)
        fg_model = np.zeros((1, 65), np.float64)
        try:
            cv2.grabCut(image_bgr, mask, (1, 1, width - 2, height - 2), bg_model, fg_model, 8, cv2.GC_INIT_WITH_MASK)
        except cv2.error as exc:
            logger.warning("GrabCut background replacement failed; using seeded foreground mask: {}", exc)

        foreground = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype("uint8")
        kernel = np.ones((5, 5), np.uint8)
        foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, kernel, iterations=2)
        foreground = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, kernel, iterations=1)
        foreground = cv2.GaussianBlur(foreground, (7, 7), 0)
        return foreground

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
