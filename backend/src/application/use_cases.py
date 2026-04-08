"""Application use cases — orchestrate domain objects via ports."""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..domain.models import Paper
from ..domain.ports import PaperFilters, PaperRepository

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


_SOURCE_TYPE_MAP: dict[str, str] = {
    "subbottom profiler": "sub-bottom profiler",
    "3.5 kHz subbottom profiler": "sub-bottom profiler",
    "airgun": "airgun array",
    "airgun array (wide-angle offshore)": "airgun array",
    "GI-gun (seismic reflection)": "GI-gun",
    "explosive (land + sea)": "explosive shots",
}


def _normalize_source_type(name: str) -> str:
    return _SOURCE_TYPE_MAP.get(name.strip(), name.strip())


_VESSEL_MAP: dict[str, str] = {
    # All R/V Robert Conrad cruise variants → canonical name
    "R/V Conrad": "R/V Robert Conrad",
    "R/V R.D. Conrad": "R/V Robert Conrad",
    # Generic multi-vessel/cruise entries
    "Multiple cruises": "Multiple vessels",
    "Multiple GEOMAR cruises": "Multiple vessels",
    # Chilean Navy vessels
    "Chilean Navy patrol vessel Cirujano Videla": "Armada de Chile vessels",
}


def _normalize_vessel(name: str) -> str:
    """Strip cruise IDs, dates and parenthetical notes for stats grouping."""
    # Remove parenthetical content: (Jan–Feb 1988), (TIPTEQ), (MD159-PACHIDERME cruise), etc.
    name = re.sub(r"\s*\([^)]*\)", "", name).strip()
    # Remove trailing cruise ID codes followed by optional cruise name:
    # SO101, SO101-102, SO-101 CONDOR, SO161 SPOC, RC2901, VG02, IT95, JC23, MV1004, M67, MD159
    name = re.sub(
        r"\s+(?:SO[-\d]+|RC\d+|VG\d+|IT\d+|JC\d+|MV\d+|MD\d+|M\d+)(?:\s+\S+)?$",
        "",
        name,
    ).strip()
    # Remove trailing lone cruise name words (CONDOR, SPOC, TIPTEQ) if any remain
    name = re.sub(r"\s+(?:CONDOR|SPOC|TIPTEQ|PACHIDERME)$", "", name).strip()
    # Normalize R.V. → R/V
    name = re.sub(r"^R\.V\.", "R/V", name)
    # Normalize case variants: OGS-EXPLORA → OGS-Explora
    name = name.replace("OGS-EXPLORA", "OGS-Explora")
    return _VESSEL_MAP.get(name, name)


def _load_pdf_stats() -> tuple[int, int, dict[str, int]]:
    """Return (pdfs_analyzed, figures_total, figures_per_paper) from images/ folder."""
    images_dir = _PROJECT_ROOT / "images"
    if not images_dir.is_dir():
        return 0, 0, {}
    figures_per_paper: dict[str, int] = {}
    for paper_dir in sorted(images_dir.iterdir()):
        if not paper_dir.is_dir():
            continue
        figs_json = paper_dir / "figures.json"
        if not figs_json.exists():
            continue
        try:
            with open(figs_json, encoding="utf-8") as f:
                data = json.load(f)
            figures_per_paper[paper_dir.name] = data.get("total_figures", 0)
        except Exception:
            figures_per_paper[paper_dir.name] = 0
    pdfs_analyzed = len(figures_per_paper)
    figures_total = sum(figures_per_paper.values())
    return pdfs_analyzed, figures_total, figures_per_paper


@dataclass
class StatsResult:
    total_papers: int
    total_datasets: int
    open_access_count: int
    restricted_count: int
    unknown_count: int
    by_region: dict[str, int]
    by_year: dict[int, int]
    by_data_type: dict[str, int]
    by_classification: dict[str, int]
    year_range: tuple[int, int]
    keyword_frequency: dict[str, int]
    by_data_format: dict[str, int]
    by_source_type: dict[str, int]
    by_vessel: dict[str, int]
    by_acq_year: dict[int, int]
    by_repository: dict[str, int]
    completeness_buckets: dict[str, int]
    avg_completeness: float
    size_gb_by_type: dict[str, float]
    datasets_by_format: dict[str, int]
    size_known_count: int
    size_unknown_count: int
    paper_field_fill: dict[str, float]
    dataset_field_fill: dict[str, float]
    pdfs_analyzed: int
    figures_total: int
    figures_per_paper: dict[str, int]


class ListPapersUseCase:
    def __init__(self, repo: PaperRepository) -> None:
        self._repo = repo

    def execute(self, filters: PaperFilters) -> list[Paper]:
        return self._repo.list_filtered(filters)


class GetPaperUseCase:
    def __init__(self, repo: PaperRepository) -> None:
        self._repo = repo

    def execute(self, paper_id: str) -> Optional[Paper]:
        return self._repo.get_by_id(paper_id)


class GetStatsUseCase:
    def __init__(self, repo: PaperRepository) -> None:
        self._repo = repo

    def execute(self) -> StatsResult:
        papers = self._repo.get_all()

        total_datasets = sum(len(p.data) for p in papers)
        open_count = sum(1 for p in papers for d in p.data if d.access == "open")
        restricted_count = sum(1 for p in papers for d in p.data if d.access == "restricted")
        unknown_count = total_datasets - open_count - restricted_count

        by_region: dict[str, int] = {}
        for p in papers:
            r = p.geographic_region
            by_region[r] = by_region.get(r, 0) + 1

        by_year: dict[int, int] = {}
        for p in papers:
            if p.year:
                by_year[p.year] = by_year.get(p.year, 0) + 1

        by_data_type: dict[str, int] = {}
        for p in papers:
            for d in p.data:
                if d.data_type:
                    by_data_type[d.data_type] = by_data_type.get(d.data_type, 0) + 1

        by_classification: dict[str, int] = {}
        for p in papers:
            for d in p.data:
                c = d.classification
                by_classification[c] = by_classification.get(c, 0) + 1

        keyword_frequency: dict[str, int] = {}
        for p in papers:
            for kw in p.keywords:
                normalized = kw.lower().strip()
                if normalized:
                    keyword_frequency[normalized] = keyword_frequency.get(normalized, 0) + 1

        by_data_format: dict[str, int] = {}
        for p in papers:
            for d in p.data:
                if d.format:
                    for fmt in d.format:
                        by_data_format[fmt] = by_data_format.get(fmt, 0) + 1

        by_source_type: dict[str, int] = {}
        for p in papers:
            if p.acquisition and p.acquisition.source_type:
                for st in p.acquisition.source_type:
                    key = _normalize_source_type(st)
                    by_source_type[key] = by_source_type.get(key, 0) + 1

        by_vessel: dict[str, int] = {}
        for p in papers:
            if p.acquisition and p.acquisition.vessel:
                for vessel in p.acquisition.vessel:
                    key = _normalize_vessel(vessel)
                    by_vessel[key] = by_vessel.get(key, 0) + 1

        by_repository: dict[str, int] = {}
        for p in papers:
            for d in p.data:
                for repo in (d.repository or []):
                    by_repository[repo] = by_repository.get(repo, 0) + 1

        by_acq_year: dict[int, int] = {}
        for p in papers:
            if p.acquisition and p.acquisition.year_acquired:
                yr = p.acquisition.year_acquired
                if isinstance(yr, list):
                    for y in yr:
                        if isinstance(y, int):
                            by_acq_year[y] = by_acq_year.get(y, 0) + 1
                elif isinstance(yr, int):
                    by_acq_year[yr] = by_acq_year.get(yr, 0) + 1

        size_gb_by_type: dict[str, float] = {}
        size_known_count = 0
        size_unknown_count = 0
        for p in papers:
            for d in p.data:
                if d.size_gb is not None:
                    size_known_count += 1
                    key = d.data_type or "unknown"
                    size_gb_by_type[key] = round(size_gb_by_type.get(key, 0.0) + d.size_gb, 2)
                else:
                    size_unknown_count += 1

        # ── per-field fill rates ──────────────────────────────────────────────
        n = len(papers) or 1

        def _pct(count: int) -> float:
            return round(count / n * 100, 1)

        def _has(val: object) -> bool:
            if val is None:
                return False
            if isinstance(val, (list, str)) and not val:
                return False
            return True

        paper_field_fill: dict[str, float] = {
            "Title":             _pct(sum(1 for p in papers if _has(p.title))),
            "Authors":           _pct(sum(1 for p in papers if _has(p.authors))),
            "Year":              _pct(sum(1 for p in papers if _has(p.year))),
            "DOI":               _pct(sum(1 for p in papers if _has(p.doi))),
            "Abstract":          _pct(sum(1 for p in papers if _has(p.abstract))),
            "Keywords":          _pct(sum(1 for p in papers if _has(p.keywords))),
            "Bounding box":      _pct(sum(1 for p in papers if p.location and p.location.bounding_box)),
            "Seismic lines":     _pct(sum(1 for p in papers if p.location and p.location.seismic_lines)),
            "Vessel":            _pct(sum(1 for p in papers if p.acquisition and _has(p.acquisition.vessel))),
            "Year acquired":     _pct(sum(1 for p in papers if p.acquisition and _has(p.acquisition.year_acquired))),
            "Source type":       _pct(sum(1 for p in papers if p.acquisition and _has(p.acquisition.source_type))),
            "Source volume":     _pct(sum(1 for p in papers if p.acquisition and p.acquisition.source_volume_cui is not None)),
            "Streamer length":   _pct(sum(1 for p in papers if p.acquisition and p.acquisition.streamer_length_m is not None)),
            "Channel count":     _pct(sum(1 for p in papers if p.acquisition and p.acquisition.channel_count is not None)),
            "Sample rate":       _pct(sum(1 for p in papers if p.acquisition and p.acquisition.sample_rate_ms is not None)),
            "Record length":     _pct(sum(1 for p in papers if p.acquisition and p.acquisition.record_length_s is not None)),
            "Fold":              _pct(sum(1 for p in papers if p.acquisition and p.acquisition.fold is not None)),
            "Shot interval":     _pct(sum(1 for p in papers if p.acquisition and p.acquisition.shot_interval_m is not None)),
            "Group interval":    _pct(sum(1 for p in papers if p.acquisition and p.acquisition.group_interval_m is not None)),
            "OBS spacing":       _pct(sum(1 for p in papers if p.acquisition and p.acquisition.obs_spacing_km is not None)),
            "Freq. range":       _pct(sum(1 for p in papers if p.acquisition and p.acquisition.frequency_range_hz is not None)),
            "Depth penetration": _pct(sum(1 for p in papers if p.acquisition and p.acquisition.depth_penetration_km is not None)),
            "Migration type":    _pct(sum(1 for p in papers if p.processing and _has(p.processing.migration_type))),
            "Tectonic setting":  _pct(sum(1 for p in papers if _has(p.tectonic_setting))),
            "Assoc. earthquakes":_pct(sum(1 for p in papers if _has(p.associated_earthquakes))),
        }

        all_datasets = [d for p in papers for d in p.data]
        nd = len(all_datasets) or 1

        def _dpct(count: int) -> float:
            return round(count / nd * 100, 1)

        dataset_field_fill: dict[str, float] = {
            "Type":        _dpct(sum(1 for d in all_datasets if _has(d.data_type))),
            "Format":      _dpct(sum(1 for d in all_datasets if _has(d.format))),
            "Repository":  _dpct(sum(1 for d in all_datasets if _has(d.repository))),
            "URL":         _dpct(sum(1 for d in all_datasets if _has(d.url))),
            "DOI":         _dpct(sum(1 for d in all_datasets if _has(d.doi))),
            "Size (GB)":   _dpct(sum(1 for d in all_datasets if d.size_gb is not None)),
            "Access":      _dpct(sum(1 for d in all_datasets if d.access != "unknown")),
            "Description": _dpct(sum(1 for d in all_datasets if _has(d.description))),
            "CDP spacing": _dpct(sum(1 for d in all_datasets if d.cdp_spacing_m is not None)),
        }

        years = [p.year for p in papers if p.year]
        year_range = (min(years), max(years)) if years else (0, 0)

        completeness_scores = [p.completeness for p in papers]
        completeness_buckets = {
            "high": sum(1 for s in completeness_scores if s >= 80),
            "medium": sum(1 for s in completeness_scores if 60 <= s < 80),
            "low": sum(1 for s in completeness_scores if s < 60),
        }
        avg_completeness = round(sum(completeness_scores) / len(completeness_scores), 1) if completeness_scores else 0.0

        pdfs_analyzed, figures_total, figures_per_paper = _load_pdf_stats()

        return StatsResult(
            total_papers=len(papers),
            total_datasets=total_datasets,
            open_access_count=open_count,
            restricted_count=restricted_count,
            unknown_count=unknown_count,
            by_region=by_region,
            by_year=by_year,
            by_data_type=by_data_type,
            by_classification=by_classification,
            year_range=year_range,
            keyword_frequency=keyword_frequency,
            by_data_format=by_data_format,
            by_source_type=by_source_type,
            by_vessel=by_vessel,
            by_acq_year=by_acq_year,
            by_repository=by_repository,
            completeness_buckets=completeness_buckets,
            avg_completeness=avg_completeness,
            size_gb_by_type=size_gb_by_type,
            datasets_by_format=by_data_format,
            size_known_count=size_known_count,
            size_unknown_count=size_unknown_count,
            paper_field_fill=paper_field_fill,
            dataset_field_fill=dataset_field_fill,
            pdfs_analyzed=pdfs_analyzed,
            figures_total=figures_total,
            figures_per_paper=figures_per_paper,
        )
