"""JSON file-based figure repository — implements the FigureRepository port."""

import json
from pathlib import Path

from ..domain.ports import FigureRepository


class JsonFigureRepository(FigureRepository):
    def __init__(self, images_dir: Path) -> None:
        self._dir = images_dir

    def get_figure_stats(self) -> tuple[int, int, dict[str, int]]:
        """Return (pdfs_analyzed, figures_total, figures_per_paper)."""
        if not self._dir.is_dir():
            return 0, 0, {}
        figures_per_paper: dict[str, int] = {}
        for paper_dir in sorted(self._dir.iterdir()):
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

    def get_preview_figures(self, paper_id: str, max_count: int = 3) -> list[str]:
        """Return up to max_count figure URL paths for a paper, or []."""
        figs_json = self._dir / paper_id / "figures.json"
        if not figs_json.exists():
            return []
        try:
            with open(figs_json, encoding="utf-8") as f:
                data = json.load(f)
            return [
                "/" + fig["path"].replace("\\", "/")
                for fig in data.get("figures", [])[:max_count]
                if fig.get("path")
            ]
        except Exception:
            return []
