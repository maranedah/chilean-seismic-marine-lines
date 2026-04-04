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
