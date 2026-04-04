# Infrastructure Review — Chilean Marine Seismic Lines

_Reviewed: 2026-04-03_

## Executive Summary

The backend hexagonal architecture is structurally sound — all layers exist and most boundaries are respected — but two routers import directly from `infrastructure/`, which is the one hard violation of the dependency rule. The frontend Atomic Design is largely correct; atoms, molecules, and organisms are well-separated, but the template layer imports an organism (Sidebar), a constant is duplicated between utils and an organism, and two app-router pages define inline atom-level primitives that belong elsewhere. Total: **2 CRITICAL, 4 WARNING, 3 INFO**.

---

## Backend — Hexagonal Architecture

### Dependency Graph (as-found)

```
domain/models.py  ←  domain/ports.py
       ↑                    ↑
application/use_cases.py ───┘
       ↑
api/schemas.py (also imports domain/models directly — allowed)
       │
api/dependencies.py  →  infrastructure/json_repository.py  →  domain/
       │                             ↑
api/routers/papers.py  ──────────────┘  ← CRITICAL: direct infra import
api/routers/stats.py   ──────────────┘  ← CRITICAL: direct infra import
       │
api/main.py (composes routers)
```

### Violations

| # | File | Severity | Rule violated | Description | Fix |
|---|------|----------|---------------|-------------|-----|
| B-1 | `api/routers/papers.py:9,25` | CRITICAL | api→infrastructure forbidden | `from ...infrastructure.json_repository import JsonPaperRepository` — used as type annotation on the `Depends` parameter | ✅ resolved 2026-04-03 — removed infra import; now annotates with `PaperRepository` |
| B-2 | `api/routers/stats.py:6,14` | CRITICAL | api→infrastructure forbidden | Same pattern — `JsonPaperRepository` imported from infrastructure just for the `Depends` type annotation | ✅ resolved 2026-04-03 — same fix as B-1 |
| B-3 | `api/dependencies.py:15` | WARNING | DI should expose port, not implementation | `get_repo()` return type is `JsonPaperRepository` (concrete) instead of `PaperRepository` (port). This forces callers to import from infrastructure to satisfy type checkers, cascading into B-1 and B-2 | ✅ resolved 2026-04-03 — return type changed to `PaperRepository` |

### Clean files

- `domain/models.py` — stdlib only; no external dependencies; exemplary
- `domain/ports.py` — imports only from `domain.models`; perfect boundary
- `application/use_cases.py` — imports from domain only; no HTTP or I/O concerns
- `infrastructure/json_repository.py` — imports from domain only; correctly implements port
- `api/main.py` — CORS config + router registration only; no layer violations
- `api/schemas.py` — correctly imports `StatsResult` from application and `Paper` from domain; adapters are clean

---

## Frontend — Atomic Design

### Component Tree (as-found)

```
app/layout.tsx
  └── templates/MainLayout.tsx
        └── organisms/Sidebar.tsx  ← WARNING: template hard-wires organism

app/page.tsx  (redirect only)

app/map/page.tsx  (data-fetch + filter + compose)
  ├── molecules/FilterBar.tsx
  │     └── [inline: Label, SelectInput, SuggestInput, NumberInput]  ← INFO
  ├── atoms/Spinner.tsx
  └── organisms/SurveyMap.tsx  (props-only, no fetch)

app/database/page.tsx  (data-fetch + filter + CSV export)
  ├── molecules/FilterBar.tsx
  ├── atoms/Spinner.tsx
  └── organisms/PapersTable.tsx  (props-only, no fetch)

app/reports/page.tsx  (data-fetch + compose)
  ├── atoms/Spinner.tsx
  └── organisms/StatsPanel.tsx
        └── atoms/MetricCard.tsx
        └── [inline: KeywordWordCloud, KeywordDistribution]  ← INFO
        └── DATA_TYPE_LABELS constant  ← WARNING (duplicated from utils/filters.ts)

app/papers/[id]/page.tsx  (data-fetch + detail view)
  ├── atoms/Badge.tsx
  ├── atoms/Button.tsx
  ├── atoms/Spinner.tsx
  ├── molecules/DatasetItem.tsx
  │     ├── atoms/Badge.tsx
  │     ├── atoms/Button.tsx
  │     └── utils/filters.ts (DATA_TYPE_LABELS)
  └── [inline: Section, Field components]  ← WARNING

services/api.ts  (pure fetch, no React)
types/paper.ts   (pure TS interfaces)
utils/filters.ts (pure functions, no React)
```

### Violations

| # | File | Severity | Rule violated | Description | Fix |
|---|------|----------|---------------|-------------|-----|
| F-1 | `templates/MainLayout.tsx:1` | WARNING | Template hard-wires organism | `Sidebar` is imported directly instead of being passed as a slot/prop. Templates must be dumb layout scaffolds; embedding a concrete organism couples the template to this specific app structure | ✅ resolved 2026-04-03 — template now accepts `sidebar: ReactNode` prop; `<Sidebar />` moved to `app/layout.tsx` |
| F-2 | `organisms/StatsPanel.tsx:29-40` | WARNING | Duplicated constant | `DATA_TYPE_LABELS` is redefined verbatim inside `StatsPanel.tsx` — it already lives in `utils/filters.ts` (line 89). Two sources of truth will diverge silently when new data types are added | ✅ resolved 2026-04-03 — local copy removed; now imports from `utils/filters` |
| F-3 | `app/papers/[id]/page.tsx:23-42` | WARNING | Atom-level primitives defined at page level | `Section` and `Field` are reusable display primitives (no state, no data-fetching) defined inline in the detail page. If a second detail-style page is added, these will be duplicated | ✅ resolved 2026-04-03 — extracted to `atoms/Section.tsx` and `atoms/Field.tsx` |
| F-4 | `molecules/FilterBar.tsx:14-89` | INFO | Atom primitives bundled into molecule | `Label`, `SelectInput`, `SuggestInput`, `NumberInput` are atom-level UI primitives defined inside the molecule file. Acceptable if FilterBar is the only consumer, but it inflates the file and makes the primitives un-reusable | Extract to `atoms/` only if another molecule needs them; otherwise tolerable as private sub-components |
| F-5 | `app/` routes (map, database, papers/[id]) | INFO | `app/` not thin wrappers; `pages/` layer absent | The intended design expects `app/` to be thin shells delegating to `pages/`, but `pages/` was never created. All data-fetching, state, and layout logic lives directly in `app/` routes. Not a dependency-rule violation, but architectural drift from the stated design | Create `pages/MapPage.tsx`, `pages/DatabasePage.tsx`, etc. and reduce `app/` entries to one-line wrappers, or formally drop the `pages/` convention |

### Clean files

- `atoms/Badge.tsx`, `atoms/Button.tsx`, `atoms/Spinner.tsx`, `atoms/MetricCard.tsx` — stateless, no side-effects, correct atom scope
- `molecules/DatasetItem.tsx` — imports only atoms and utils; no API calls; clean molecule
- `organisms/Sidebar.tsx` — navigation state via `usePathname` only; no data-fetching; correct scope
- `organisms/SurveyMap.tsx` — receives data via props; no direct API calls; router navigation only
- `organisms/PapersTable.tsx` — local sort state only; no API calls; clean
- `organisms/StatsPanel.tsx` — receives stats via props; no API calls (aside from the duplicated constant in F-2)
- `app/layout.tsx` — thin shell; clean
- `app/page.tsx` — redirect only; clean
- `app/reports/page.tsx` — minimal: one query, one conditional render, delegates to organism
- `services/api.ts` — no React imports, no JSX; pure fetch functions
- `types/paper.ts` — pure TypeScript interfaces; no logic
- `utils/filters.ts` — no React, no side-effects; pure functions

---

## Priority Fix List

Ordered by impact:

1. **[CRITICAL — B-1/B-2]** Fix `api/routers/papers.py` and `api/routers/stats.py` — direct infrastructure imports break the hexagonal dependency rule; the whole point of `PaperRepository` as an abstract port is to keep routers decoupled from the JSON implementation. Swap in 3 lines: change `get_repo()` return type to `PaperRepository`, remove the two `JsonPaperRepository` imports from the routers, update the type annotations.

2. **[WARNING — B-3]** Fix `api/dependencies.py` return type — this is what forces violations B-1 and B-2; fixing this first unblocks the router fixes and enforces the port contract at the only place it should be broken.

3. **[WARNING — F-2]** Remove duplicated `DATA_TYPE_LABELS` from `organisms/StatsPanel.tsx` — simplest one-line fix; eliminates a silent maintenance hazard where adding a new data type to `utils/filters.ts` will not be reflected in the stats charts.

4. **[WARNING — F-1]** Decouple `Sidebar` from `templates/MainLayout.tsx` — medium effort; makes the template genuinely reusable and testable in isolation.

5. **[WARNING — F-3]** Extract `Section`/`Field` from `app/papers/[id]/page.tsx` — low effort; prevents duplication if a second detail view is ever added.

---

## Review Notes

_2026-04-03: First review. The backend is one `get_repo()` return-type change away from being architecturally clean — B-1 and B-2 are entirely caused by B-3 leaking the concrete type outward. The frontend atoms layer is in excellent shape; the violations are all in the composition layers. No circular imports were found anywhere. The `pages/` directory convention was never implemented — the `app/` router files serve as both entry points and pages, which is pragmatic but should be either formally adopted or corrected before the component tree grows._

_2026-04-03: All CRITICAL and WARNING violations resolved in the same session. B-1/B-2/B-3 fixed by changing `get_repo()` return type to `PaperRepository` and removing infrastructure imports from routers. F-1 fixed by making `MainLayout` accept `sidebar` as a prop. F-2 fixed by removing the duplicate `DATA_TYPE_LABELS` constant from `StatsPanel`. F-3 fixed by extracting `Section` and `Field` to `atoms/Section.tsx` and `atoms/Field.tsx`. Remaining open items are INFO-level only (F-4 inline atom primitives in FilterBar, F-5 absent pages/ layer)._
