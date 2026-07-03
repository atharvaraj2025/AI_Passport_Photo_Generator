"""Centralized Loguru setup."""
import sys
from loguru import logger
from app.config import Settings

def configure_logging(settings: Settings) -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO", enqueue=True, backtrace=False, diagnose=False)
    logger.add(settings.log_dir / "app.log", rotation="10 MB", retention="14 days", compression="zip", level="DEBUG", enqueue=True)
