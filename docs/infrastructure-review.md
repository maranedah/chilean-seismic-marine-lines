# Infrastructure Review — Chilean Marine Seismic Lines

_Reviewed: 2026-04-08_

## Executive Summary

Backend, frontend, and root hygiene are fully clean — all prior violations resolved. The first full audit of `src/` reveals significant structural problems: **16 CRITICAL** violations from module-level side effects (bare `for` loops, file writes, HTTP calls at import time) across the 11 `probe/` experiment files and 5 `tools/` scripts that lack `if __name__ == "__main__"` guards; **4 WARNING** violations in `extract/` and `downloader/` files (missing `main()`/argparse, module-level stdout reconfiguration, and a session object created at import time); **5 INFO** items for oversized functions. The dominant concern is the `tools/` scripts that modify production data files whenever imported — these require immediate wrapping in `main()` guards.

---

## Backend — Hexagonal Architecture

### Dependency Graph (as-found)

```
domain/models.py  ←  domain/ports.py
       ↑                    ↑
application/use_cases.py ───┘
  └── _load_pdf_stats()  ← WARNING B-4: direct file I/O bypasses port
       ↑
api/schemas.py
  ├── imports StatsResult ← application  (allowed)
  ├── imports Paper ← domain             (allowed)
  └── _load_preview_figures()  ← WARNING B-5: infrastructure code in API layer

api/dependencies.py  →  infrastructure/json_repository.py  →  domain/
       │
api/routers/papers.py  (clean — uses PaperRepository port)
api/routers/stats.py   (clean — uses PaperRepository port)
api/main.py (composes routers)
```

### Violations

| # | File | Severity | Rule violated | Description | Fix |
|---|------|----------|---------------|-------------|-----|
| B-1 | `api/routers/papers.py:9,25` | CRITICAL | api→infrastructure forbidden | `from ...infrastructure.json_repository import JsonPaperRepository` | ✅ resolved 2026-04-03 |
| B-2 | `api/routers/stats.py:6,14` | CRITICAL | api→infrastructure forbidden | `JsonPaperRepository` imported from infrastructure for `Depends` type | ✅ resolved 2026-04-03 |
| B-3 | `api/dependencies.py:15` | WARNING | DI should expose port, not implementation | `get_repo()` return type was concrete `JsonPaperRepository` instead of `PaperRepository` | ✅ resolved 2026-04-03 |
| B-4 | `application/use_cases.py:61–81` | WARNING | Infrastructure concern in application layer | `_load_pdf_stats()` reads the filesystem directly (`data/extracted_images/*/figures.json`) inside `GetStatsUseCase.execute()`. File I/O is an infrastructure concern; it should be behind an abstract port (e.g. `PdfStatsRepository`) injected via the constructor | ✅ resolved 2026-04-08 — added `FigureRepository` port to `domain/ports.py`; implemented in `infrastructure/figure_repository.py`; injected into `GetStatsUseCase.__init__` |
| B-5 | `api/schemas.py:16–30` | WARNING | Infrastructure concern in presentation layer | `_load_preview_figures()` opens JSON files from disk to build preview URLs. Filesystem access in the schema/adapter layer mixes I/O with serialisation | ✅ resolved 2026-04-08 — removed helper; `to_paper_summary()` now accepts `preview_figures: list[str]`; list is fetched by router via injected `FigureRepository` |
| B-6 | `application/use_cases.py:12` | INFO | Hardcoded path bypasses DI | `_PROJECT_ROOT = Path(__file__).resolve().parents[3]` fragile path lookup | ✅ resolved 2026-04-08 — `_PROJECT_ROOT` removed from `use_cases.py`; path lives only in `api/dependencies.py` |

### Clean files

- `domain/models.py` — stdlib only; no external dependencies; exemplary
- `domain/ports.py` — imports only from `domain.models`; perfect boundary
- `infrastructure/json_repository.py` — imports from domain only; correctly implements port
- `api/dependencies.py` — correctly wires infrastructure into port; return type is `PaperRepository`
- `api/main.py` — CORS config + router registration only; no layer violations
- `api/routers/papers.py` — uses `PaperRepository` port; no infra imports
- `api/routers/stats.py` — uses `PaperRepository` port; no infra imports

---

## Frontend — Atomic Design

### Component Tree (as-found)

```
app/layout.tsx
  └── templates/MainLayout.tsx (sidebar: ReactNode slot — clean)
        ├── organisms/Sidebar.tsx
        └── <children>

app/page.tsx  (redirect only — clean)

app/map/page.tsx  (useQuery → fetchPapers, applyFilters, compose)
  ├── molecules/FilterBar.tsx
  │     └── [private: Label, SelectInput, SuggestInput, NumberInput]  ← INFO F-4
  ├── atoms/Spinner.tsx
  └── organisms/SurveyMap.tsx  (props-only)

app/database/page.tsx  (useQuery → fetchPapers, applyFilters, CSV export)
  ├── molecules/FilterBar.tsx
  ├── atoms/Spinner.tsx
  └── organisms/PapersTable.tsx  (props-only)

app/reports/page.tsx  (useQuery → fetchStats, compose)
  ├── atoms/Spinner.tsx
  └── organisms/StatsPanel.tsx [699 lines — INFO F-8]
        └── [private: TabCard, PapersTab, DatasetsTab, QualityTab,
                    PdfAnalysisSection, FieldCoverageTable, HorizontalBar]

app/papers/[id]/page.tsx  (useQuery → fetchPaper + inline fetchFigures)
  ├── fetchFigures() defined inline  ← WARNING F-6
  ├── GalleryImage organism embedded in page  ← INFO F-7
  ├── atoms/Badge.tsx, Button.tsx, Field.tsx, Section.tsx, Spinner.tsx
  └── molecules/DatasetItem.tsx

src/providers.tsx  ← INFO F-9 (misplaced — should be src/app/providers.tsx)

services/api.ts    (pure fetch — clean)
types/paper.ts     (pure TS interfaces — clean)
utils/filters.ts   (pure functions — clean)
```

### Violations

| # | File | Severity | Rule violated | Description | Fix |
|---|------|----------|---------------|-------------|-----|
| F-1 | `templates/MainLayout.tsx` | WARNING | Template hard-wired organism | `Sidebar` imported directly inside template | ✅ resolved 2026-04-03 — now accepts `sidebar: ReactNode` prop |
| F-2 | `organisms/StatsPanel.tsx` | WARNING | Duplicated constant | `DATA_TYPE_LABELS` redefined inline; also in `utils/filters.ts` | ✅ resolved 2026-04-03 — imports from `utils/filters` |
| F-3 | `app/papers/[id]/page.tsx` | WARNING | Atom primitives at page level | `Section` and `Field` defined inline | ✅ resolved 2026-04-03 — extracted to `atoms/Section.tsx` and `atoms/Field.tsx` |
| F-4 | `molecules/FilterBar.tsx:14–89` | INFO | Atom primitives bundled into molecule | `Label`, `SelectInput`, `SuggestInput`, `NumberInput` are atom-level UI primitives defined as private helpers inside the molecule file. Not exported, so not an import-direction violation, but inflates file size and makes primitives un-reusable | Extract to `atoms/` only when a second consumer appears; tolerable as private sub-components for now |
| F-5 | `app/` routes (map, database, papers/[id]) | INFO | `pages/` layer absent | Data-fetching, state, and layout logic live directly in `app/` routes rather than in a `pages/` layer with thin `app/` wrappers. Pragmatic but drifts from the stated design | Formally adopt `app/` as the page layer (update the layer map) or create `pages/MapPage.tsx`, etc. |
| F-6 | `app/papers/[id]/page.tsx:30–38` | WARNING | Data-fetching outside service layer | `fetchFigures()` defined inline in page file instead of `services/api.ts` | ✅ resolved 2026-04-08 — moved to `services/api.ts`; `FigureEntry`/`FiguresManifest` moved to `types/paper.ts` |
| F-7 | `app/papers/[id]/page.tsx:40–106` | INFO | Organism-level component in page file | `GalleryImage` manages expanded/modal state and renders a full-screen overlay — organism-scope behaviour | ✅ resolved 2026-04-08 — extracted to `organisms/GalleryImage.tsx` |
| F-8 | `organisms/StatsPanel.tsx` | INFO | God component (699 lines) | Contains 7+ private sub-function components | ✅ resolved 2026-04-08 — split into `organisms/StatsPanel.tsx` (shell, ~90 lines) + `organisms/stats/PapersTab.tsx`, `organisms/stats/DatasetsTab.tsx`, `organisms/stats/QualityTab.tsx`, `organisms/stats/charts.tsx` (shared helpers) |
| F-9 | `src/providers.tsx` | INFO | Provider outside `app/` | `providers.tsx` lived at `src/` root | ✅ resolved 2026-04-08 — moved to `src/app/providers.tsx`; import in `layout.tsx` updated |

### Clean files

- `atoms/Badge.tsx`, `atoms/Button.tsx`, `atoms/Spinner.tsx`, `atoms/MetricCard.tsx`, `atoms/Section.tsx`, `atoms/Field.tsx` — stateless, no side-effects, correct atom scope
- `molecules/DatasetItem.tsx` — imports only atoms and utils; no API calls; clean molecule
- `organisms/Sidebar.tsx` — navigation state via `usePathname` only; no data-fetching; correct scope
- `organisms/SurveyMap.tsx` — receives data via props; no direct API calls; clean
- `organisms/PapersTable.tsx` — local sort state only; no API calls; clean
- `organisms/StatsPanel.tsx` — receives stats via props; no API calls; imports `DATA_TYPE_LABELS` from utils correctly
- `templates/MainLayout.tsx` — pure layout scaffold; no business logic
- `app/layout.tsx` — thin shell; clean
- `app/page.tsx` — redirect only; clean
- `app/reports/page.tsx` — minimal: one query, one conditional render, delegates to organism
- `services/api.ts` — no React imports, no JSX; pure fetch functions
- `types/paper.ts` — pure TypeScript interfaces; no logic
- `utils/filters.ts` — no React, no side-effects; pure functions

---

## Root / `scripts/` Folder Hygiene

### Misplaced files

| # | File | Severity | Proposed location under `src/` | Reason |
|---|------|----------|---------------------------------|--------|
| H-1 | `sync_to_gcs.py` | WARNING | `src/tools/sync_to_gcs.py` | Standalone runnable script at project root | ✅ resolved 2026-04-08 — moved; `_PROJECT_ROOT` path updated to `parents[2]`; old file deleted |
| H-2 | `scripts/frontend_lint.py` | WARNING | `src/tools/frontend_lint.py` | Runnable script in `scripts/` | ✅ resolved 2026-04-08 — moved; `cwd` path updated; `.pre-commit-config.yaml` entry updated |
| H-3 | `scripts/frontend_typecheck.py` | WARNING | `src/tools/frontend_typecheck.py` | Same as H-2 | ✅ resolved 2026-04-08 — same as H-2 |
| H-4 | `data/extracted_jsons/temp_update_status.py` | INFO | Delete | Temporary script in data directory | ✅ resolved 2026-04-08 — deleted |
| H-5 | `data/extracted_jsons/temp_stats.py` | INFO | Delete | Same as H-4 | ✅ resolved 2026-04-08 — deleted |

---

## Priority Fix List

Ordered by impact:

1. **[WARNING — B-4]** Extract `_load_pdf_stats()` from `application/use_cases.py` — the application layer should never open files directly; define a `PdfStatsPort` ABC in `domain/ports.py`, implement in `infrastructure/`, and inject it into `GetStatsUseCase`. This is the most architecturally meaningful fix remaining. ✅ resolved 2026-04-08

2. **[WARNING — B-5]** Move `_load_preview_figures()` out of `api/schemas.py` — file I/O in the serialisation layer is the second instance of the same problem; refactor so the path is resolved in the use-case or injected, and the schema adapter receives it as a plain list. ✅ resolved 2026-04-08

3. **[WARNING — F-6]** Move `fetchFigures()` to `services/api.ts` — one-function change that closes the gap in the API client surface and makes the function available to any future consumer without importing a page module. ✅ resolved 2026-04-08

4. **[WARNING — H-1/H-2/H-3]** Relocate `sync_to_gcs.py`, `scripts/frontend_lint.py`, and `scripts/frontend_typecheck.py` to `src/tools/` — three file moves; delete the `scripts/` directory once empty. ✅ resolved 2026-04-08

5. **[INFO — F-7]** Extract `GalleryImage` to `organisms/GalleryImage.tsx` — worthwhile before any second detail-view page is added; also move the `FigureEntry`/`FiguresManifest` types to `types/paper.ts`. ✅ resolved 2026-04-08

6. **[INFO — H-4/H-5]** Delete `data/extracted_jsons/temp_update_status.py` and `temp_stats.py` — zero-risk cleanup. ✅ resolved 2026-04-08

7. **[CRITICAL — S-12/S-13/S-14/S-15/S-16]** Wrap bare `tools/` scripts (`backfill.py`, `backfill_data_types.py`, `find_urls.py`, `fix_urls.py`, `inventory_pangaea.py`) in `main()` + `if __name__ == "__main__"` guards — five files that mutate production JSON data unconditionally on import; any `import` or `python -c` will corrupt data.

8. **[CRITICAL — S-1 through S-11]** Delete all 11 `src/probe/` files — pure experiment scratch-pad with module-level HTTP calls and file writes; `probe/` should not exist in committed code.

9. **[WARNING — S-17/S-18/S-19]** Add `main()` + argparse to `extract/pdf_text.py`, `extract/fields.py`, `extract/resolution.py`; move `sys.stdout.reconfigure()` inside the guard — makes these files safe to import and consistent with the rest of the pipeline.

10. **[WARNING — S-20]** Move `SESSION = requests.Session()` in `downloader/pdfs.py` inside `main()` — avoids creating an HTTP connection pool at import time.

---

## `src/` Pipeline Architecture

### Module map (as-found)

```
src/
├── scraper/    [5 files: pangaea.py, mgds.py, geofon.py, pangaea_batch.py, mgds_batch.py]
├── enrich/     [3 files: mgds.py, rvdata.py, pangaea.py]
├── extract/    [4 files: figures.py, pdf_text.py, fields.py, resolution.py]
├── downloader/ [2 files: datasets.py, pdfs.py]
├── tools/      [10 files: backfill.py, backfill_data_types.py, find_urls.py, fix_urls.py,
│                          inventory_pangaea.py, check_access.py, normalize_fields.py,
│                          sync_to_gcs.py, frontend_lint.py, frontend_typecheck.py]
└── probe/      [11 files — should be 0]
```

### Import graph (as-found)

```
scraper/pangaea_batch.py → scraper/pangaea.py   (batch orchestrator → single-item worker)
scraper/mgds_batch.py   → scraper/mgds.py       (same pattern)

No cross-module imports between unrelated pipeline stages found.
All enrich/, extract/, downloader/, and tools/ files are self-contained.
```

### Violations

| # | File | Severity | Rule | Description | Fix |
|---|------|----------|------|-------------|-----|
| S-1 | `probe/pangaea_api.py` | CRITICAL | P-1, P-3 | Module-level `for` loops that make HTTP calls to PANGAEA API | ✅ resolved 2026-04-08 — deleted |
| S-2 | `probe/pangaea_api2.py` | CRITICAL | P-1, P-2, P-3 | Numbered iteration file; bare loops with HTTP at module level | ✅ resolved 2026-04-08 — deleted |
| S-3 | `probe/pangaea_api3.py` | CRITICAL | P-1, P-2, P-3 | Numbered; module-level prints and loop | ✅ resolved 2026-04-08 — deleted |
| S-4 | `probe/pangaea_api4.py` | CRITICAL | P-1, P-2, P-3 | Numbered; bare loops | ✅ resolved 2026-04-08 — deleted |
| S-5 | `probe/pangaea_api5.py` | CRITICAL | P-1, P-2, P-3 | Numbered; bare loops + HTML scraping | ✅ resolved 2026-04-08 — deleted |
| S-6 | `probe/pangaea_api6.py` | CRITICAL | P-1, P-2, P-3 | Numbered; bare loops | ✅ resolved 2026-04-08 — deleted |
| S-7 | `probe/pangaea_final.py` | CRITICAL | P-1, P-3 | Module-level `requests.get()` and `print()` calls | ✅ resolved 2026-04-08 — deleted |
| S-8 | `probe/datacite.py` | CRITICAL | P-1, P-3 | Module-level test loop calling `search_datacite()` | ✅ resolved 2026-04-08 — deleted |
| S-9 | `probe/datacite2.py` | CRITICAL | P-1, P-2, P-3 | Numbered; bare API call loops | ✅ resolved 2026-04-08 — deleted |
| S-10 | `probe/datacite3.py` | CRITICAL | P-1, P-2, P-3 | Numbered; `json.dump(..., open(...))` write at module level | ✅ resolved 2026-04-08 — deleted |
| S-11 | `probe/datacite4.py` | CRITICAL | P-1, P-2, P-3 | Numbered; bare loops + `json.dump` at module level | ✅ resolved 2026-04-08 — deleted (`probe/` directory removed) |
| S-12 | `tools/backfill.py` | CRITICAL | P-1, P-5 | Entire file runs at module level — no guard; writes `_backfill_result.txt` on import | ✅ resolved 2026-04-08 — wrapped in `main()` + `if __name__ == "__main__"` |
| S-13 | `tools/backfill_data_types.py` | CRITICAL | P-1, P-5 | Bare `for` loop (lines 39–58) modifies paper JSONs unconditionally at import time | ✅ resolved 2026-04-08 — same fix |
| S-14 | `tools/find_urls.py` | CRITICAL | P-1, P-5 | Bare `for` loop + `open(ROOT / "_urls.txt", "w")` at module level | ✅ resolved 2026-04-08 — same fix |
| S-15 | `tools/fix_urls.py` | CRITICAL | P-1, P-5 | Bare `for` loop (lines 103–122) that patches paper JSONs at module level | ✅ resolved 2026-04-08 — same fix |
| S-16 | `tools/inventory_pangaea.py` | CRITICAL | P-1, P-5 | Bare `for` loop + `write_text()` writing `_pangaea_map.json` at module level | ✅ resolved 2026-04-08 — same fix |
| S-17 | `extract/pdf_text.py:7` | WARNING | P-1, P-5 | `sys.stdout.reconfigure()` at module level (line 7, no guard); no `main()`, no argparse | ✅ resolved 2026-04-08 — moved reconfigure inside `main()`; added argparse |
| S-18 | `extract/fields.py:28` | WARNING | P-1, P-5 | Same: `sys.stdout.reconfigure()` naked at line 28; no `main()`, no argparse | ✅ resolved 2026-04-08 — same fix |
| S-19 | `extract/resolution.py` | WARNING | P-5 | No `main()` function, no argparse (guard exists but is bare `sys.argv` loop) | ✅ resolved 2026-04-08 — added `main()` with argparse |
| S-20 | `downloader/pdfs.py:51` | WARNING | P-1 | `SESSION = requests.Session()` at module level — creates HTTP connection pool at import time | ✅ resolved 2026-04-08 — `SESSION` declared as type annotation only; initialized via `global SESSION` at top of `main()` |
| S-21 | `extract/figures.py:216–497` | INFO | P-7 | `extract()` function is ~280 lines (file is 511 total); mixes caption extraction, image grouping, page-render fallback, and manifest writing | ✅ resolved 2026-04-08 — extracted `_collect_image_rects()` (steps 2+3), `_render_page_fallback()` (step 3b), `_write_manifest()` (step 5); `extract()` reduced to ~80 lines |
| S-22 | `scraper/pangaea.py` | INFO | P-4, P-7 | 376-line file; `parse_pangaea_tab()` at 137 lines mixed HTTP fetch, line splitting, and metadata parsing | ✅ resolved 2026-04-08 — extracted `_split_tab_lines()` and `_parse_meta_block()`; `parse_pangaea_tab()` reduced to ~80 lines |
| S-23 | `scraper/mgds.py` | INFO | P-7 | 469 lines; `enrich_sensor()` at 78 lines mixed URL dispatch, detail merging, and schema mapping | ✅ resolved 2026-04-08 — extracted `_fetch_sensor_detail()` (URL dispatch) and `_build_dataset_entry()` (schema mapping); `enrich_sensor()` reduced to 3 lines |
| S-24 | `tools/frontend_lint.py` | INFO | P-5 | Pre-commit hook script; all code at top level with no `if __name__ == "__main__"` guard | ✅ resolved 2026-04-08 — wrapped in `main()` + guard |
| S-25 | `tools/frontend_typecheck.py` | INFO | P-5 | Same as S-24 | ✅ resolved 2026-04-08 — same fix |

### Clean files

- `scraper/geofon.py` — `main()`, argparse, guard; stdout/stderr reconfigure inside `if hasattr()` conditional
- `scraper/pangaea_batch.py` — clean batch orchestrator; imports `pangaea.py` correctly
- `scraper/mgds_batch.py` — clean batch orchestrator; imports `mgds.py` correctly
- `enrich/mgds.py` — `main()`, argparse, guard; correct `Path(__file__).parent.parent.parent` anchoring
- `enrich/rvdata.py` — same; clean
- `enrich/pangaea.py` — same; clean
- `downloader/datasets.py` — `main()`, argparse, guard; fully clean
- `tools/check_access.py` — exemplary: `main()`, argparse, guard, well-structured helper functions
- `tools/normalize_fields.py` — `main()`, argparse, guard; clean
- `tools/sync_to_gcs.py` — `main()`, argparse, guard; correct `parents[2]` path anchoring

---

## Review Notes

_2026-04-03: First review. The backend is one `get_repo()` return-type change away from being architecturally clean — B-1 and B-2 are entirely caused by B-3 leaking the concrete type outward. The frontend atoms layer is in excellent shape; the violations are all in the composition layers. No circular imports were found anywhere. The `pages/` directory convention was never implemented — the `app/` router files serve as both entry points and pages, which is pragmatic but should be either formally adopted or corrected before the component tree grows._

_2026-04-03: All CRITICAL and WARNING violations resolved in the same session. B-1/B-2/B-3 fixed by changing `get_repo()` return type to `PaperRepository` and removing infrastructure imports from routers. F-1 fixed by making `MainLayout` accept `sidebar` as a prop. F-2 fixed by removing the duplicate `DATA_TYPE_LABELS` constant from `StatsPanel`. F-3 fixed by extracting `Section` and `Field` to `atoms/Section.tsx` and `atoms/Field.tsx`. Remaining open items are INFO-level only (F-4 inline atom primitives in FilterBar, F-5 absent pages/ layer)._

_2026-04-08: Second review. All previously resolved violations confirmed clean. Three new WARNING violations found: B-4 (file I/O in application use-case), B-5 (file I/O in API schemas), F-6 (inline fetch function in page). Three new INFO violations: F-7 (GalleryImage organism in page file), F-8 (StatsPanel God component), F-9 (providers.tsx misplaced in src/ root). Root hygiene audit added: five misplaced files found — sync_to_gcs.py at root, two scripts in scripts/, two temp scripts in data/. The pattern of direct file-system access leaking across layers (B-4, B-5) is the dominant backend concern; both stem from the absence of a port for PDF/figure metadata._

_2026-04-08: All second-review violations resolved in the same session. B-4/B-6 fixed by adding `FigureRepository` port to `domain/ports.py` and `JsonFigureRepository` in `infrastructure/figure_repository.py`; injected into `GetStatsUseCase` and wired in `dependencies.py`. B-5 fixed by removing `_load_preview_figures` from `schemas.py`; preview figures now passed as a parameter fetched by the router via the same `FigureRepository`. F-6 fixed by moving `fetchFigures` to `services/api.ts` and types to `types/paper.ts`. F-7 fixed by extracting `GalleryImage` to `organisms/GalleryImage.tsx`. F-8 fixed by splitting 699-line `StatsPanel.tsx` into a shell + `organisms/stats/{PapersTab,DatasetsTab,QualityTab,charts}.tsx`. F-9 fixed by moving `providers.tsx` to `src/app/providers.tsx`. All five root hygiene files relocated or deleted; `.pre-commit-config.yaml` updated. No open violations remain._

_2026-04-08: All INFO-level src/ violations resolved. S-21: `extract/figures.py` `extract()` split into `_collect_image_rects()`, `_render_page_fallback()`, `_write_manifest()` — function reduced from ~280 to ~80 lines. S-22: `scraper/pangaea.py` `parse_pangaea_tab()` split via `_split_tab_lines()` and `_parse_meta_block()` — reduced from ~137 to ~80 lines. S-23: `scraper/mgds.py` `enrich_sensor()` split into `_fetch_sensor_detail()` and `_build_dataset_entry()` — `enrich_sensor()` is now 3 lines. All src/ violations fully resolved; no open items remain._

_2026-04-08: Third review violations resolved in the same session. All 11 `probe/` files and the `probe/` directory deleted. Five `tools/` scripts (`backfill.py`, `backfill_data_types.py`, `find_urls.py`, `fix_urls.py`, `inventory_pangaea.py`) wrapped in `def main()` + `if __name__ == "__main__": main()` guards. Three `extract/` files fixed: `pdf_text.py` and `fields.py` had naked `sys.stdout.reconfigure()` moved inside `main()` and argparse added; `resolution.py` gained `main()` + argparse. `downloader/pdfs.py` `SESSION` moved from module level to `main()` via `global SESSION`. `tools/frontend_lint.py` and `tools/frontend_typecheck.py` wrapped in `main()` + guard. Remaining open items are INFO-level only (S-21/S-22/S-23 complexity refactors)._

_2026-04-08: Third review — first full audit of `src/` pipeline completed (new Step 5c added to infrastructure-reviewer skill). 16 CRITICAL violations found: all 11 `probe/` files violate P-1 (module-level HTTP calls and bare loops) and P-3 (scratch directory must not exist); 5 `tools/` scripts (`backfill.py`, `backfill_data_types.py`, `find_urls.py`, `fix_urls.py`, `inventory_pangaea.py`) run production-data mutations unconditionally at module level with no `if __name__ == "__main__"` guard. 4 WARNING violations: `extract/pdf_text.py` and `extract/fields.py` have naked `sys.stdout.reconfigure()` at module level and no `main()`/argparse; `extract/resolution.py` lacks `main()`/argparse; `downloader/pdfs.py` creates `SESSION = requests.Session()` at module level. 5 INFO items: `extract/figures.py` has a 280-line `extract()` function; `scraper/pangaea.py` (376 lines) and `scraper/mgds.py` (469 lines) mix HTTP/parse/I/O; two pre-commit hook scripts lack guards. No cross-module imports between unrelated pipeline stages found. The `tools/` P-1 violations are the most urgent — they corrupt data files whenever accidentally imported._
