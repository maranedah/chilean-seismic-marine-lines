"""Application use cases — orchestrate domain objects via ports."""

from dataclasses import dataclass
from typing import Optional

from ..domain.models import Paper
from ..domain.ports import PaperFilters, PaperRepository


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
    completeness_buckets: dict[str, int]
    avg_completeness: float


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
                    by_data_format[d.format] = by_data_format.get(d.format, 0) + 1

        by_source_type: dict[str, int] = {}
        for p in papers:
            if p.acquisition and p.acquisition.source_type:
                st = p.acquisition.source_type
                by_source_type[st] = by_source_type.get(st, 0) + 1

        by_vessel: dict[str, int] = {}
        for p in papers:
            if p.acquisition and p.acquisition.vessel:
                vessel = p.acquisition.vessel.split("(")[0].strip()
                by_vessel[vessel] = by_vessel.get(vessel, 0) + 1

        by_acq_year: dict[int, int] = {}
        for p in papers:
            if p.acquisition and p.acquisition.year_acquired:
                yr = p.acquisition.year_acquired
                by_acq_year[yr] = by_acq_year.get(yr, 0) + 1

        years = [p.year for p in papers if p.year]
        year_range = (min(years), max(years)) if years else (0, 0)

        completeness_scores = [p.completeness for p in papers]
        completeness_buckets = {
            "high": sum(1 for s in completeness_scores if s >= 80),
            "medium": sum(1 for s in completeness_scores if 60 <= s < 80),
            "low": sum(1 for s in completeness_scores if s < 60),
        }
        avg_completeness = round(sum(completeness_scores) / len(completeness_scores), 1) if completeness_scores else 0.0

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
            completeness_buckets=completeness_buckets,
            avg_completeness=avg_completeness,
        )
