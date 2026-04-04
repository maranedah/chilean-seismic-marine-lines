"""FastAPI dependency injection — provides a singleton repository."""

import os
from pathlib import Path

from ..domain.ports import PaperRepository
from ..infrastructure.json_repository import JsonPaperRepository

_repo: JsonPaperRepository | None = None


def get_repo() -> PaperRepository:
    global _repo
    if _repo is None:
        _env = os.environ.get("PAPERS_DIR")
        papers_dir = Path(_env) if _env else Path(__file__).resolve().parents[4] / "papers"
        _repo = JsonPaperRepository(papers_dir)
    return _repo
