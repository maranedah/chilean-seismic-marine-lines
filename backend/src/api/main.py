"""FastAPI application entry point."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

_images_env = os.environ.get("IMAGES_DIR")
_images_dir = Path(_images_env) if _images_env else Path(__file__).resolve().parents[4] / "images"
if _images_dir.is_dir():
    app.mount("/images", StaticFiles(directory=str(_images_dir)), name="images")


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}
