"""Pydantic response schemas and domain→schema adapters."""

from typing import Optional

from pydantic import BaseModel

from ..application.use_cases import StatsResult
from ..domain.models import Paper


# ── Response schemas ──────────────────────────────────────────────────────────


class BoundingBoxSchema(BaseModel):
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float


class SeismicLineSchema(BaseModel):
    name: str
    lat_start: Optional[float] = None
    lon_start: Optional[float] = None
    lat_end: Optional[float] = None
    lon_end: Optional[float] = None
    length_km: Optional[float] = None
    depth_km: Optional[float] = None
    profile_orientation: Optional[str] = None


class LocationSchema(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: str = ""
    region: str = ""
    country: str = ""
    description: str = ""
    bounding_box: Optional[BoundingBoxSchema] = None
    seismic_lines: list[SeismicLineSchema] = []


class AcquisitionSchema(BaseModel):
    vessel: Optional[list[str]] = None
    expeditions: Optional[list[str]] = None
    year_acquired: Optional[int] = None
    source_type: Optional[list[str]] = None
    source_volume_cui: Optional[float] = None
    streamer_length_m: Optional[float] = None
    channel_count: Optional[int] = None
    sample_rate_ms: Optional[float] = None
    record_length_s: Optional[float] = None
    fold: Optional[int] = None
    line_spacing_km: Optional[float] = None
    shot_interval_m: Optional[float] = None
    group_interval_m: Optional[float] = None
    obs_spacing_km: Optional[float] = None
    nearest_offset_m: Optional[float] = None
    frequency_range_hz: Optional[list[float]] = None
    depth_penetration_km: Optional[float] = None


class DatasetSchema(BaseModel):
    data_type: str = ""
    name: str = ""
    classification: str = "PROCESSED"
    format: Optional[list[str]] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    repository: Optional[list[str]] = None
    size_gb: Optional[float] = None
    access: str = "unknown"
    download_command: Optional[str] = None
    description: str = ""
    cdp_spacing_m: Optional[float] = None


class ProcessingSchema(BaseModel):
    classification: str = "PROCESSED"
    summary: str = ""
    workflow: list[str] = []
    software: list[str] = []
    notes: Optional[str] = None
    migration_type: Optional[str] = None


class PaperSchema(BaseModel):
    id: str
    title: str
    authors: list[str] = []
    year: int = 0
    journal: str = ""
    doi: Optional[str] = None
    url: Optional[str] = None
    open_access_url: Optional[str] = None
    abstract: Optional[str] = None
    keywords: list[str] = []
    location: Optional[LocationSchema] = None
    acquisition: Optional[AcquisitionSchema] = None
    data: list[DatasetSchema] = []
    processing: Optional[ProcessingSchema] = None
    analysis_confidence: Optional[str] = None
    analysis_notes: Optional[str] = None
    tectonic_setting: Optional[str] = None
    associated_earthquakes: list[str] = []
    # computed
    geographic_region: str = ""
    paper_url: Optional[str] = None
    has_open_data: bool = False
    access_types: list[str] = []
    data_types: list[str] = []
    classifications: list[str] = []
    completeness: float = 0.0


class PaperSummarySchema(BaseModel):
    """Lightweight version for list/map views."""

    id: str
    title: str
    authors_short: str
    authors: list[str] = []
    year: int
    journal: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: str = ""
    geographic_region: str = ""
    paper_url: Optional[str] = None
    has_open_data: bool = False
    access_types: list[str] = []
    data_types: list[str] = []
    classifications: list[str] = []
    num_datasets: int = 0
    keywords: list[str] = []
    open_access_paper: bool = False
    vessel: Optional[list[str]] = None
    acq_year: Optional[int] = None
    source_type: Optional[list[str]] = None
    data_formats: list[str] = []
    repositories: list[str] = []
    seismic_lines: list[SeismicLineSchema] = []
    completeness: float = 0.0
    preview_figures: list[str] = []


class StatsSchema(BaseModel):
    total_papers: int
    total_datasets: int
    open_access_count: int
    restricted_count: int
    unknown_count: int
    by_region: dict[str, int]
    by_year: dict[str, int]
    by_data_type: dict[str, int]
    by_classification: dict[str, int]
    year_range: list[int]
    keyword_frequency: dict[str, int] = {}
    by_data_format: dict[str, int] = {}
    by_source_type: dict[str, int] = {}
    by_vessel: dict[str, int] = {}
    by_acq_year: dict[str, int] = {}
    by_repository: dict[str, int] = {}
    completeness_buckets: dict[str, int] = {}
    avg_completeness: float = 0.0
    size_gb_by_type: dict[str, float] = {}
    datasets_by_format: dict[str, int] = {}
    size_known_count: int = 0
    size_unknown_count: int = 0
    paper_field_fill: dict[str, float] = {}
    dataset_field_fill: dict[str, float] = {}
    pdfs_analyzed: int = 0
    figures_total: int = 0
    figures_per_paper: dict[str, int] = {}


# ── Adapters ──────────────────────────────────────────────────────────────────


def _authors_short(authors: list[str]) -> str:
    first_three = [a.split(",")[0].strip() for a in authors[:3]]
    suffix = " et al." if len(authors) > 3 else ""
    return ", ".join(first_three) + suffix


def to_paper_summary(paper: Paper, preview_figures: list[str] | None = None) -> PaperSummarySchema:
    lat = paper.location.latitude if paper.location else None
    lon = paper.location.longitude if paper.location else None
    city = paper.location.city if paper.location else ""

    acq = paper.acquisition
    return PaperSummarySchema(
        id=paper.id,
        title=paper.title,
        authors_short=_authors_short(paper.authors),
        authors=paper.authors,
        year=paper.year,
        journal=paper.journal,
        latitude=lat,
        longitude=lon,
        city=city,
        geographic_region=paper.geographic_region,
        paper_url=paper.paper_url,
        open_access_paper=paper.open_access_url is not None,
        has_open_data=paper.has_open_data,
        access_types=paper.access_types,
        data_types=paper.data_types,
        classifications=paper.classifications,
        num_datasets=len(paper.data),
        keywords=paper.keywords,
        vessel=acq.vessel if acq else None,
        acq_year=acq.year_acquired if acq else None,
        source_type=acq.source_type if acq else None,
        data_formats=list({fmt for d in paper.data if d.format for fmt in d.format}),
        repositories=list({repo for d in paper.data if d.repository for repo in d.repository}),
        seismic_lines=(
            [
                SeismicLineSchema(
                    name=sl.name,
                    lat_start=sl.lat_start,
                    lon_start=sl.lon_start,
                    lat_end=sl.lat_end,
                    lon_end=sl.lon_end,
                    length_km=sl.length_km,
                    depth_km=sl.depth_km,
                    profile_orientation=sl.profile_orientation,
                )
                for sl in paper.location.seismic_lines
            ]
            if paper.location
            else []
        ),
        completeness=paper.completeness,
        preview_figures=preview_figures or [],
    )


def to_paper_schema(paper: Paper) -> PaperSchema:
    loc = paper.location
    location_schema = (
        LocationSchema(
            latitude=loc.latitude,
            longitude=loc.longitude,
            city=loc.city,
            region=loc.region,
            country=loc.country,
            description=loc.description,
            bounding_box=(
                BoundingBoxSchema(
                    lat_min=loc.bounding_box.lat_min,
                    lat_max=loc.bounding_box.lat_max,
                    lon_min=loc.bounding_box.lon_min,
                    lon_max=loc.bounding_box.lon_max,
                )
                if loc.bounding_box
                else None
            ),
            seismic_lines=[
                SeismicLineSchema(
                    name=sl.name,
                    lat_start=sl.lat_start,
                    lon_start=sl.lon_start,
                    lat_end=sl.lat_end,
                    lon_end=sl.lon_end,
                    length_km=sl.length_km,
                    depth_km=sl.depth_km,
                    profile_orientation=sl.profile_orientation,
                )
                for sl in loc.seismic_lines
            ],
        )
        if loc
        else None
    )

    acq = paper.acquisition
    acquisition_schema = (
        AcquisitionSchema(
            vessel=acq.vessel,
            expeditions=acq.expeditions,
            year_acquired=acq.year_acquired,
            source_type=acq.source_type,
            source_volume_cui=acq.source_volume_cui,
            streamer_length_m=acq.streamer_length_m,
            channel_count=acq.channel_count,
            sample_rate_ms=acq.sample_rate_ms,
            record_length_s=acq.record_length_s,
            fold=acq.fold,
            line_spacing_km=acq.line_spacing_km,
            shot_interval_m=acq.shot_interval_m,
            group_interval_m=acq.group_interval_m,
            obs_spacing_km=acq.obs_spacing_km,
            nearest_offset_m=acq.nearest_offset_m,
            frequency_range_hz=acq.frequency_range_hz,
            depth_penetration_km=acq.depth_penetration_km,
        )
        if acq
        else None
    )

    proc = paper.processing
    processing_schema = (
        ProcessingSchema(
            classification=proc.classification,
            summary=proc.summary,
            workflow=proc.workflow,
            software=proc.software,
            notes=proc.notes,
            migration_type=proc.migration_type,
        )
        if proc
        else None
    )

    return PaperSchema(
        id=paper.id,
        title=paper.title,
        authors=paper.authors,
        year=paper.year,
        journal=paper.journal,
        doi=paper.doi,
        url=paper.url,
        open_access_url=paper.open_access_url,
        abstract=paper.abstract,
        keywords=paper.keywords,
        location=location_schema,
        acquisition=acquisition_schema,
        data=[
            DatasetSchema(
                data_type=d.data_type,
                name=d.name,
                classification=d.classification,
                format=d.format,
                url=d.url,
                doi=d.doi,
                repository=d.repository,
                size_gb=d.size_gb,
                access=d.access,
                download_command=d.download_command,
                description=d.description,
                cdp_spacing_m=d.cdp_spacing_m,
            )
            for d in paper.data
        ],
        processing=processing_schema,
        analysis_confidence=paper.analysis_confidence,
        analysis_notes=paper.analysis_notes,
        tectonic_setting=paper.tectonic_setting,
        associated_earthquakes=paper.associated_earthquakes,
        geographic_region=paper.geographic_region,
        paper_url=paper.paper_url,
        has_open_data=paper.has_open_data,
        access_types=paper.access_types,
        data_types=paper.data_types,
        classifications=paper.classifications,
        completeness=paper.completeness,
    )


def to_stats_schema(stats: StatsResult) -> StatsSchema:
    return StatsSchema(
        total_papers=stats.total_papers,
        total_datasets=stats.total_datasets,
        open_access_count=stats.open_access_count,
        restricted_count=stats.restricted_count,
        unknown_count=stats.unknown_count,
        by_region=stats.by_region,
        by_year={str(k): v for k, v in stats.by_year.items()},
        by_data_type=stats.by_data_type,
        by_classification=stats.by_classification,
        year_range=list(stats.year_range),
        keyword_frequency=stats.keyword_frequency,
        by_data_format=stats.by_data_format,
        by_source_type=stats.by_source_type,
        by_vessel=stats.by_vessel,
        by_acq_year={str(k): v for k, v in stats.by_acq_year.items()},
        by_repository=stats.by_repository,
        completeness_buckets=stats.completeness_buckets,
        avg_completeness=stats.avg_completeness,
        size_gb_by_type=stats.size_gb_by_type,
        datasets_by_format=stats.datasets_by_format,
        size_known_count=stats.size_known_count,
        size_unknown_count=stats.size_unknown_count,
        paper_field_fill=stats.paper_field_fill,
        dataset_field_fill=stats.dataset_field_fill,
        pdfs_analyzed=stats.pdfs_analyzed,
        figures_total=stats.figures_total,
        figures_per_paper=stats.figures_per_paper,
    )
