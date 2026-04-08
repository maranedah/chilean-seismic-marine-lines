"""FastAPI application entry point."""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from .routers import papers, stats

app = FastAPI(
    title="Chilean Marine Seismic Lines API",
    description="REST API for the Chilean marine seismic survey database.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(papers.router)
app.include_router(stats.router)

_GCS_BUCKET = os.environ.get("GCS_BUCKET")

if _GCS_BUCKET:
    # Production: proxy image and preview requests to GCS.
    from google.api_core.exceptions import NotFound
    from google.cloud import storage as _gcs

    _gcs_client = _gcs.Client()

    def _gcs_response(prefix: str, paper_id: str, filename: str) -> StreamingResponse:
        blob = _gcs_client.bucket(_GCS_BUCKET).blob(f"{prefix}/{paper_id}/{filename}")
        try:
            data = blob.download_as_bytes()
        except NotFound:
            raise HTTPException(status_code=404, detail="Not found.")
        suffix = filename.rsplit(".", 1)[-1].lower()
        content_type = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "json": "application/json",
        }.get(suffix, "application/octet-stream")
        return StreamingResponse(iter([data]), media_type=content_type)

    @app.get("/images/{paper_id}/{filename}", tags=["images"])
    def get_image(paper_id: str, filename: str) -> StreamingResponse:
        return _gcs_response("data/extracted_images", paper_id, filename)

    @app.get("/previews/{paper_id}/{filename}", tags=["images"])
    def get_preview(paper_id: str, filename: str) -> StreamingResponse:
        return _gcs_response("data/extracted_images_low_res", paper_id, filename)

else:
    # Development / local Docker: serve images directly from the filesystem.
    _images_env = os.environ.get("IMAGES_DIR")
    _images_dir = (
        Path(_images_env)
        if _images_env
        else Path(__file__).resolve().parents[4] / "data" / "extracted_images"
    )
    if _images_dir.is_dir():
        app.mount("/images", StaticFiles(directory=str(_images_dir)), name="images")


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}
