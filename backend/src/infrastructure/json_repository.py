"""JSON file adapter — implements the PaperRepository port."""

import json
from pathlib import Path
from typing import Optional

from ..domain.models import (
    Acquisition,
    BoundingBox,
    Dataset,
    Location,
    Paper,
    Processing,
    SeismicLine,
)
from ..domain.ports import PaperFilters, PaperRepository

_EXCLUDE = {"survey_results.json", "data_availability.json", "schema.json"}


class JsonPaperRepository(PaperRepository):
    def __init__(self, papers_dir: Path) -> None:
        self._dir = papers_dir
        self._cache: Optional[list[Paper]] = None

    # ── internal ──────────────────────────────────────────────────────────────

    def _load_all(self) -> list[Paper]:
        if self._cache is not None:
            return self._cache
        papers: list[Paper] = []
        for f in sorted(self._dir.glob("*.json")):
            if f.name in _EXCLUDE:
                continue
            try:
                with open(f, encoding="utf-8") as fh:
                    papers.append(self._parse(json.load(fh)))
            except Exception:
                continue
        self._cache = papers
        return papers

    def _parse(self, data: dict) -> Paper:
        loc_data = data.get("location") or {}
        bb_raw = loc_data.get("bounding_box")
        bb = BoundingBox(**bb_raw) if bb_raw else None

        lines = [
            SeismicLine(
                name=line.get("name", ""),
                lat_start=line.get("lat_start"),
                lon_start=line.get("lon_start"),
                lat_end=line.get("lat_end"),
                lon_end=line.get("lon_end"),
                length_km=line.get("length_km"),
            )
            for line in loc_data.get("seismic_lines", [])
        ]

        location = (
            Location(
                latitude=loc_data.get("latitude"),
                longitude=loc_data.get("longitude"),
                city=loc_data.get("city", ""),
                region=loc_data.get("region", ""),
                country=loc_data.get("country", ""),
                description=loc_data.get("description", ""),
                bounding_box=bb,
                seismic_lines=lines,
            )
            if loc_data
            else None
        )

        acq_raw = data.get("acquisition") or {}
        acquisition = (
            Acquisition(
                vessel=acq_raw.get("vessel"),
                year_acquired=acq_raw.get("year_acquired"),
                source_type=acq_raw.get("source_type"),
                source_volume_cui=acq_raw.get("source_volume_cui"),
                streamer_length_m=acq_raw.get("streamer_length_m"),
                channel_count=acq_raw.get("channel_count"),
                sample_rate_ms=acq_raw.get("sample_rate_ms"),
                record_length_s=acq_raw.get("record_length_s"),
                fold=acq_raw.get("fold"),
                line_spacing_km=acq_raw.get("line_spacing_km"),
            )
            if acq_raw
            else None
        )

        datasets = [
            Dataset(
                data_type=d.get("data_type", ""),
                name=d.get("name", ""),
                classification=d.get("classification", "PROCESSED"),
                format=d.get("format"),
                url=d.get("url"),
                doi=d.get("doi"),
                repository=d.get("repository"),
                size_gb=d.get("size_gb"),
                access=d.get("access", "unknown"),
                download_command=d.get("download_command"),
                description=d.get("description", ""),
            )
            for d in data.get("data", [])
            if not d.get("_data_note")
        ]

        proc_raw = data.get("processing") or {}
        processing = (
            Processing(
                classification=proc_raw.get("classification", "PROCESSED"),
                summary=proc_raw.get("summary", ""),
                workflow=proc_raw.get("workflow", []),
                software=proc_raw.get("software", []),
                notes=proc_raw.get("notes"),
            )
            if proc_raw
            else None
        )

        return Paper(
            id=data.get("id", ""),
            title=data.get("title", ""),
            authors=data.get("authors", []),
            year=data.get("year", 0),
            journal=data.get("journal", ""),
            doi=data.get("doi"),
            url=data.get("url"),
            open_access_url=data.get("open_access_url"),
            abstract=data.get("abstract"),
            keywords=data.get("keywords", []),
            location=location,
            acquisition=acquisition,
            data=datasets,
            processing=processing,
            analysis_confidence=data.get("analysis_confidence"),
            analysis_notes=data.get("analysis_notes"),
        )

    # ── port implementation ───────────────────────────────────────────────────

    def get_all(self) -> list[Paper]:
        return self._load_all()

    def get_by_id(self, paper_id: str) -> Optional[Paper]:
        return next((p for p in self._load_all() if p.id == paper_id), None)

    def list_filtered(self, filters: PaperFilters) -> list[Paper]:
        result = []
        for p in self._load_all():
            if filters.region and p.geographic_region != filters.region:
                continue
            if filters.year_min and p.year < filters.year_min:
                continue
            if filters.year_max and p.year > filters.year_max:
                continue
            if filters.access and filters.access not in p.access_types:
                continue
            if filters.classification and filters.classification not in p.classifications:
                continue
            if filters.open_only and not p.has_open_data:
                continue
            if filters.data_types and not any(dt in p.data_types for dt in filters.data_types):
                continue
            if filters.q:
                q_lower = filters.q.lower()
                city = p.location.city if p.location else ""
                if not (
                    q_lower in p.title.lower()
                    or any(q_lower in a.lower() for a in p.authors)
                    or any(q_lower in kw.lower() for kw in p.keywords)
                    or q_lower in city.lower()
                    or q_lower in p.journal.lower()
                ):
                    continue
            result.append(p)
        return result
