"""Pydantic response schemas for passport processing."""
from pydantic import BaseModel, Field
from typing import Literal

class ErrorDetail(BaseModel):
    filename: str | None = None
    message: str
    code: str = "processing_error"

class ProcessedPhoto(BaseModel):
    original_filename: str
    output_filename: str
    download_url: str
    width: int
    height: int
    faces_detected: int = Field(ge=1)
    background_mode: Literal["original", "solid"]

class ProcessingSummary(BaseModel):
    total: int
    successful: int
    failed: int
    elapsed_seconds: float
    results: list[ProcessedPhoto] = Field(default_factory=list)
    errors: list[ErrorDetail] = Field(default_factory=list)

class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    model_loaded: bool
