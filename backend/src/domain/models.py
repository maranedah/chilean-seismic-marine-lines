"""Domain entities — pure Python, no external dependencies."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BoundingBox:
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float


@dataclass
class SeismicLine:
    name: str
    lat_start: Optional[float] = None
    lon_start: Optional[float] = None
    lat_end: Optional[float] = None
    lon_end: Optional[float] = None
    length_km: Optional[float] = None
    depth_km: Optional[float] = None
    profile_orientation: Optional[str] = None


@dataclass
class Location:
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: str = ""
    region: str = ""
    country: str = ""
    description: str = ""
    bounding_box: Optional[BoundingBox] = None
    seismic_lines: list[SeismicLine] = field(default_factory=list)


@dataclass
class Acquisition:
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


@dataclass
class Dataset:
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


@dataclass
class Processing:
    classification: str = "PROCESSED"
    summary: str = ""
    workflow: list[str] = field(default_factory=list)
    software: list[str] = field(default_factory=list)
    notes: Optional[str] = None
    migration_type: Optional[str] = None


@dataclass
class Paper:
    id: str
    title: str
    authors: list[str] = field(default_factory=list)
    year: int = 0
    journal: str = ""
    doi: Optional[str] = None
    url: Optional[str] = None
    open_access_url: Optional[str] = None
    abstract: Optional[str] = None
    keywords: list[str] = field(default_factory=list)
    location: Optional[Location] = None
    acquisition: Optional[Acquisition] = None
    data: list[Dataset] = field(default_factory=list)
    processing: Optional[Processing] = None
    analysis_confidence: Optional[str] = None
    analysis_notes: Optional[str] = None
    tectonic_setting: Optional[str] = None
    associated_earthquakes: list[str] = field(default_factory=list)

    @property
    def geographic_region(self) -> str:
        lat = self.location.latitude if self.location else None
        if lat is None:
            return "Unknown"
        if lat >= -30:
            return "North Chile (17°–30°S)"
        if lat >= -40:
            return "Central Chile (30°–40°S)"
        return "South Chile (40°–57°S)"

    @property
    def paper_url(self) -> Optional[str]:
        return self.open_access_url or self.url

    @property
    def has_open_data(self) -> bool:
        return any(d.url for d in self.data)

    @property
    def access_types(self) -> list[str]:
        return list({d.access for d in self.data})

    @property
    def data_types(self) -> list[str]:
        return sorted({d.data_type for d in self.data if d.data_type})

    @property
    def classifications(self) -> list[str]:
        return list({d.classification for d in self.data})

    @property
    def completeness(self) -> float:
        checks = [
            bool(self.title),
            bool(self.authors),
            bool(self.year),
            bool(self.doi),
            bool(self.abstract),
            bool(self.keywords),
            self.location is not None,
            self.location is not None and self.location.bounding_box is not None,
            self.location is not None and len(self.location.seismic_lines) > 0,
            self.acquisition is not None,
            self.acquisition is not None and bool(self.acquisition.vessel),
            bool(self.data),
        ]
        return round(sum(checks) / len(checks) * 100)
