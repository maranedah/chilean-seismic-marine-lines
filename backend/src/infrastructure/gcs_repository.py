"""GCS-backed repository implementations.

Uses Application Default Credentials (ADC). Set GOOGLE_APPLICATION_CREDENTIALS
to a service-account key file, or rely on Workload Identity when running on GCP.
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import PurePosixPath
from typing import Optional

from google.cloud import storage

from ..domain.models import Paper
from ..domain.ports import FigureRepository
from .json_repository import JsonPaperRepository, _EXCLUDE

_MAX_WORKERS = 10


class GcsPaperRepository(JsonPaperRepository):
    """Reads paper JSON files from GCS instead of the local filesystem."""

    def __init__(self, bucket_name: str, prefix: str = "data/extracted_jsons") -> None:
        self._bucket_name = bucket_name
        self._prefix = prefix.rstrip("/")
        self._cache: Optional[list[Paper]] = None
        self._client = storage.Client()
        # Do NOT call super().__init__ — no local dir needed.

    def _load_all(self) -> list[Paper]:
        if self._cache is not None:
            return self._cache

        bucket = self._client.bucket(self._bucket_name)

        # Filter to relevant blobs first (cheap list call)
        blobs = [
            blob
            for blob in bucket.list_blobs(prefix=self._prefix + "/")
            if not _should_skip(blob.name, self._prefix)
        ]

        def _download(blob: storage.Blob) -> Optional[Paper]:
            try:
                data = json.loads(blob.download_as_text(encoding="utf-8"))
                return self._parse(data)
            except Exception:
                return None

        papers: list[Paper] = []
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            futures = {pool.submit(_download, blob): blob for blob in blobs}
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    papers.append(result)

        # Stable sort by id to keep deterministic ordering
        papers.sort(key=lambda p: p.id)
        self._cache = papers
        return papers


class GcsFigureRepository(FigureRepository):
    """Reads figure metadata from GCS and returns /images/... proxy URLs."""

    def __init__(self, bucket_name: str, prefix: str = "data/extracted_images") -> None:
        self._bucket_name = bucket_name
        self._prefix = prefix.rstrip("/")
        self._client = storage.Client()
        # Lazily populated: {paper_id: figures_json_dict}
        self._cache: Optional[dict[str, dict]] = None

    # ── internal ──────────────────────────────────────────────────────────────

    def _load_cache(self) -> dict[str, dict]:
        """Download all figures.json files in parallel, once."""
        if self._cache is not None:
            return self._cache

        bucket = self._client.bucket(self._bucket_name)

        # Collect (paper_id, blob) pairs for every figures.json
        pairs: list[tuple[str, storage.Blob]] = []
        for blob in bucket.list_blobs(prefix=self._prefix + "/"):
            rel = blob.name[len(self._prefix) + 1:]
            parts = rel.split("/")
            if len(parts) == 2 and parts[1] == "figures.json":
                pairs.append((parts[0], blob))

        def _download(paper_id: str, blob: storage.Blob) -> tuple[str, dict]:
            try:
                data = json.loads(blob.download_as_text(encoding="utf-8"))
                return paper_id, data
            except Exception:
                return paper_id, {}

        cache: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            futures = {pool.submit(_download, pid, blob): pid for pid, blob in pairs}
            for future in as_completed(futures):
                paper_id, data = future.result()
                cache[paper_id] = data

        self._cache = cache
        return cache

    # ── port implementation ───────────────────────────────────────────────────

    def get_figure_stats(self) -> tuple[int, int, dict[str, int]]:
        cache = self._load_cache()
        figures_per_paper = {pid: d.get("total_figures", 0) for pid, d in cache.items()}
        return len(figures_per_paper), sum(figures_per_paper.values()), figures_per_paper

    def get_preview_figures(self, paper_id: str, max_count: int = 3) -> list[str]:
        cache = self._load_cache()
        data = cache.get(paper_id, {})
        result: list[str] = []
        for fig in data.get("figures", [])[:max_count]:
            raw_path = fig.get("path", "")
            if not raw_path:
                continue
            # Low-res previews are stored as JPEG regardless of the original format.
            stem = PurePosixPath(raw_path.replace("\\", "/")).stem
            result.append(f"/previews/{paper_id}/{stem}.jpg")
        return result


# ── helpers ───────────────────────────────────────────────────────────────────

def _should_skip(blob_name: str, prefix: str) -> bool:
    rel = blob_name[len(prefix) + 1:]
    return "/" in rel or not rel.endswith(".json") or rel in _EXCLUDE
