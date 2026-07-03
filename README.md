# AI Passport Photo Generator

A complete local-only FastAPI + React + Vite application for generating professional passport-size photographs. The backend uses InsightFace for **face detection only**: it detects the largest face, aligns a passport-style crop with forehead, chin, and shoulders, resizes to 413 × 531, and saves JPEG files at quality 95.

## Features

- Single, multiple, HEIC/HEIF, WEBP, PNG, JPEG, and ZIP uploads.
- ZIP extraction that ignores folders, hidden files, and unsupported entries.
- EXIF orientation correction before face detection.
- Optional colored background or original background.
- Batch download as `passport_photos.zip`.
- Modern responsive React dashboard with dark/light mode, drag and drop, progress, statistics, history, result gallery, downloads, and cleanup.

## Requirements

- Python 3.12+
- Node.js 20+
- npm

## Installation

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs on `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The web app runs on `http://localhost:5173`.

## Configuration

Backend configuration lives in `backend/.env`. You can configure upload limits, output size, JPEG quality, CORS origins, model name, provider, and default background color.

## API Documentation

- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

- `GET /`
- `GET /health`
- `POST /api/passport/single`
- `POST /api/passport/multiple`
- `POST /api/passport/zip`
- `GET /api/download/{filename}`
- `GET /api/download/all`
- `DELETE /api/cleanup`

## Supported Formats

Images: JPG, JPEG, PNG, WEBP, HEIC, HEIF. Archives: ZIP. Maximum image size is 10 MB, maximum ZIP size is 500 MB, and maximum image count is 1000 by default.

## Project Structure

```text
backend/app/api        FastAPI routes
backend/app/services   Processing orchestration and image logic
backend/app/models     InsightFace detector wrapper
backend/app/schemas    Pydantic response schemas
backend/app/utils      Logging and file helpers
frontend/src/components UI components
frontend/src/pages      Home, About, Settings, History sections
frontend/src/services   Axios API client
frontend/src/contexts   Theme context
```

## Screenshots Placeholder

Add screenshots of the dashboard, upload card, and result gallery after running the local app.

## Troubleshooting

- If InsightFace model download is slow, run the backend once with internet access so the model cache is populated.
- If HEIC files do not open, ensure `pillow-heif` installed successfully for your platform.
- If uploads fail due to size, adjust `MAX_IMAGE_SIZE_MB` or `MAX_ZIP_SIZE_MB` in `backend/.env`.
- If CORS blocks requests, add your frontend origin to `CORS_ORIGINS`.

## Future Improvements

- Browser-side preview comparison slider.
- Optional background matting for precise replacement.
- Country-specific passport templates.
- WebSocket progress events for very large batches.
