"""FastAPI dependency injection — provides singleton repository instances.

When the GCS_BUCKET environment variable is set the app reads all data from
Google Cloud Storage (production). Otherwise it falls back to the local
filesystem (development / local Docker).
"""

import os
from pathlib import Path

from ..domain.ports import FigureRepository, PaperRepository

_repo: PaperRepository | None = None
_figure_repo: FigureRepository | None = None


def _project_root() -> Path:
    # Only called in local fallback mode; safe to compute here.
    return Path(__file__).resolve().parents[3]


def get_repo() -> PaperRepository:
    global _repo
    if _repo is None:
        gcs_bucket = os.environ.get("GCS_BUCKET")
        if gcs_bucket:
            from ..infrastructure.gcs_repository import GcsPaperRepository
            _repo = GcsPaperRepository(gcs_bucket)
        else:
            from ..infrastructure.json_repository import JsonPaperRepository
            _env = os.environ.get("PAPERS_DIR")
            papers_dir = Path(_env) if _env else _project_root() / "data" / "extracted_jsons"
            _repo = JsonPaperRepository(papers_dir)
    return _repo


def get_figure_repo() -> FigureRepository:
    global _figure_repo
    if _figure_repo is None:
        gcs_bucket = os.environ.get("GCS_BUCKET")
        if gcs_bucket:
            from ..infrastructure.gcs_repository import GcsFigureRepository
            _figure_repo = GcsFigureRepository(gcs_bucket)
        else:
            from ..infrastructure.figure_repository import JsonFigureRepository
            _env = os.environ.get("IMAGES_DIR")
            images_dir = Path(_env) if _env else _project_root() / "data" / "extracted_images"
            _figure_repo = JsonFigureRepository(images_dir)
    return _figure_repo
