"""Abstract repository interface (port) — no concrete dependencies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from .models import Paper


@dataclass
class PaperFilters:
    region: Optional[str] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    access: Optional[str] = None
    classification: Optional[str] = None
    open_only: bool = False
    data_types: list[str] = field(default_factory=list)
    q: Optional[str] = None


class PaperRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[Paper]: ...

    @abstractmethod
    def get_by_id(self, paper_id: str) -> Optional[Paper]: ...

    @abstractmethod
    def list_filtered(self, filters: PaperFilters) -> list[Paper]: ...


class FigureRepository(ABC):
    """Port for reading extracted figure metadata from any storage backend."""

    @abstractmethod
    def get_figure_stats(self) -> tuple[int, int, dict[str, int]]:
        """Return (pdfs_analyzed, figures_total, figures_per_paper)."""
        ...

    @abstractmethod
    def get_preview_figures(self, paper_id: str, max_count: int = 3) -> list[str]:
        """Return up to max_count figure URL paths for a paper, or []."""
        ...
