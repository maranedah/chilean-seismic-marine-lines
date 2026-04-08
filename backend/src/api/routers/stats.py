"""Stats endpoint."""

from fastapi import APIRouter, Depends

from ...application.use_cases import GetStatsUseCase
from ...domain.ports import FigureRepository, PaperRepository
from ..dependencies import get_figure_repo, get_repo
from ..schemas import StatsSchema, to_stats_schema

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsSchema)
def get_stats(
    repo: PaperRepository = Depends(get_repo),
    figure_repo: FigureRepository = Depends(get_figure_repo),
) -> StatsSchema:
    stats = GetStatsUseCase(repo, figure_repo).execute()
    return to_stats_schema(stats)
