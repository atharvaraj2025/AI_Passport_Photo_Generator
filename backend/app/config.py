"""Application configuration loaded from environment variables."""
from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parent

class Settings(BaseSettings):
    """Runtime settings for the passport photo API."""
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Passport Photo Generator"
    app_version: str = "1.0.0"
    api_prefix: str = "/api"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])
    upload_dir: Path = BACKEND_DIR / "app" / "uploads"
    output_dir: Path = BACKEND_DIR / "app" / "outputs"
    temp_dir: Path = BACKEND_DIR / "app" / "temp"
    log_dir: Path = BACKEND_DIR / "app" / "logs"
    max_image_size_mb: int = 10
    max_zip_size_mb: int = 500
    max_images: int = 1000
    output_width: int = 413
    output_height: int = 531
    jpeg_quality: int = 95
    insightface_model: str = "buffalo_l"
    insightface_providers: list[str] = Field(default_factory=lambda: ["CPUExecutionProvider"])
    default_background: str = "original"
    solid_background_color: str = "#ffffff"
    request_timeout_seconds: int = 600

    @property
    def allowed_image_extensions(self) -> set[str]:
        return {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}

    @property
    def allowed_extensions(self) -> set[str]:
        return self.allowed_image_extensions | {".zip"}

    @property
    def max_image_bytes(self) -> int:
        return self.max_image_size_mb * 1024 * 1024

    @property
    def max_zip_bytes(self) -> int:
        return self.max_zip_size_mb * 1024 * 1024

    def ensure_directories(self) -> None:
        for directory in (self.upload_dir, self.output_dir, self.temp_dir, self.log_dir):
            directory.mkdir(parents=True, exist_ok=True)

@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
