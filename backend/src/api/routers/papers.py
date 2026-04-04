"""Papers endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from ...application.use_cases import GetPaperUseCase, ListPapersUseCase
from ...domain.ports import PaperFilters, PaperRepository
from ..dependencies import get_repo
from ..schemas import PaperSchema, PaperSummarySchema, to_paper_schema, to_paper_summary

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.get("", response_model=list[PaperSummarySchema])
def list_papers(
    region: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    access: Optional[str] = None,
    classification: Optional[str] = None,
    open_only: bool = False,
    data_types: Optional[str] = None,
    q: Optional[str] = None,
    repo: PaperRepository = Depends(get_repo),
) -> list[PaperSummarySchema]:
    filters = PaperFilters(
        region=region,
        year_min=year_min,
        year_max=year_max,
        access=access,
        classification=classification,
        open_only=open_only,
        data_types=data_types.split(",") if data_types else [],
        q=q,
    )
    papers = ListPapersUseCase(repo).execute(filters)
    return [to_paper_summary(p) for p in papers]


@router.get("/{paper_id}", response_model=PaperSchema)
def get_paper(
    paper_id: str,
    repo: PaperRepository = Depends(get_repo),
) -> PaperSchema:
    paper = GetPaperUseCase(repo).execute(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail=f"Paper '{paper_id}' not found.")
    return to_paper_schema(paper)
