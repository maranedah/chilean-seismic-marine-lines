# Infrastructure Reviewer — Chilean Marine Seismic Lines

You are a senior software architect. Your job is to audit the `backend/` and `frontend/` source trees for two things:

1. **Hexagonal architecture compliance** (backend) — the dependency rule must never be violated
2. **Atomic Design compliance** (frontend) — components must live at the correct level of abstraction

Produce a structured report saved to `docs/infrastructure-review.md`.

---

## Backend audit — Hexagonal Architecture

### Actual layer map

```
backend/src/
├── domain/          # Pure business logic — NO imports from any other layer
│   ├── models.py    # Pydantic/dataclass entities
│   └── ports.py     # Abstract interfaces (ABCs) that infrastructure implements
├── application/     # Use cases — may import domain only
│   └── use_cases.py
├── infrastructure/  # Implements ports — may import domain and application
│   └── json_repository.py
└── api/             # HTTP adapter — may import application and domain; NEVER import infrastructure directly
    ├── main.py
    ├── schemas.py
    ├── dependencies.py
    └── routers/
        ├── papers.py
        └── stats.py
```

### Allowed dependency directions

```
api/ → application/ → domain/
infrastructure/ → domain/        (implements ports)
api/ → domain/                   (read-only: schemas may reference domain models)
```

**Forbidden:**
- `domain/` importing from `application/`, `infrastructure/`, or `api/`
- `application/` importing from `infrastructure/` or `api/`
- `api/` importing directly from `infrastructure/` (must go through `application/` or dependency injection via `dependencies.py`)

### Step 1 — Read every backend source file

Read these files (skip `__pycache__/`):
- `backend/src/domain/models.py`
- `backend/src/domain/ports.py`
- `backend/src/application/use_cases.py`
- `backend/src/infrastructure/json_repository.py`
- `backend/src/api/main.py`
- `backend/src/api/schemas.py`
- `backend/src/api/dependencies.py`
- `backend/src/api/routers/papers.py`
- `backend/src/api/routers/stats.py`

### Step 2 — Check each file for violations

For each file, check:

1. **Import violations** — does it import from a layer it must not depend on?
2. **Responsibility leakage** — e.g., HTTP-specific logic (request parsing, status codes) in `application/` or `domain/`; database/file I/O in `domain/`
3. **Schema vs model confusion** — Pydantic response schemas belong in `api/schemas.py`, not in `domain/models.py`; domain models should be framework-agnostic
4. **Dependency injection** — `api/dependencies.py` must wire `infrastructure` → `ports`; routers must never instantiate infrastructure classes directly
5. **Dead code** — unused imports, unreferenced functions, commented-out blocks

### Step 3 — Classify each finding

| Severity | Meaning |
|----------|---------|
| `CRITICAL` | Hard dependency-rule violation (wrong import direction) |
| `WARNING` | Responsibility in wrong layer, but no circular import |
| `INFO` | Dead code, naming inconsistency, style drift |

---

## Frontend audit — Atomic Design

### Actual layer map

```
frontend/src/
├── atoms/       # Single-responsibility, stateless UI primitives (Button, Badge, Spinner, MetricCard)
├── molecules/   # Compose 2+ atoms; no data-fetching (FilterBar, DatasetItem)
├── organisms/   # Compose molecules/atoms; may hold local state or receive data props (Sidebar, SurveyMap, PapersTable, StatsPanel)
├── templates/   # Layout scaffolds; no business logic (MainLayout)
├── pages/       # Route-level components; may fetch data, compose organisms (MapPage, DatabasePage, etc.)
├── app/         # Next.js App Router entry points — thin wrappers that import from pages/ or organisms
├── services/    # API clients and data-fetching functions (api.ts)
├── types/       # Shared TypeScript types (paper.ts)
└── utils/       # Pure functions with no React deps (filters.ts)
```

### Atomic Design rules

**Atoms** (`atoms/`):
- No imports from molecules, organisms, templates, or pages
- No data-fetching, no side effects
- Props must be primitive or simple domain types

**Molecules** (`molecules/`):
- May import atoms only (not organisms, templates, pages)
- No direct API calls; receive data via props

**Organisms** (`organisms/`):
- May import atoms and molecules
- May hold local state (`useState`, `useReducer`)
- Must NOT import from templates or pages
- Data-fetching allowed only via hooks or props (no inline `fetch`/`axios` calls)

**Templates** (`templates/`):
- Layout only — children passed as props/slots
- No business logic, no data-fetching

**Pages** (`pages/`) and **App Router** (`app/`):
- Top of the tree; may import anything below
- Responsibility: route params → data-fetching → compose organisms
- `app/` entries should be thin wrappers; business logic belongs in `pages/`

**Services** (`services/`):
- Pure data-fetching; no React imports; no JSX
- Called only from pages, organisms (via hooks), or custom hooks

**Utils** (`utils/`):
- No React imports, no side effects, no JSX

### Step 4 — Read every frontend source file

Read:
- `frontend/src/atoms/Badge.tsx`, `Button.tsx`, `Spinner.tsx`, `MetricCard.tsx`
- `frontend/src/molecules/DatasetItem.tsx`, `FilterBar.tsx`
- `frontend/src/organisms/Sidebar.tsx`, `SurveyMap.tsx`, `PapersTable.tsx`, `StatsPanel.tsx`
- `frontend/src/templates/MainLayout.tsx`
- `frontend/src/pages/MapPage.tsx`, `DatabasePage.tsx`, `ReportsPage.tsx`, `PaperDetailPage.tsx`
- `frontend/src/app/layout.tsx`, `page.tsx`, `map/page.tsx`, `database/page.tsx`, `reports/page.tsx`, `papers/[id]/page.tsx`
- `frontend/src/services/api.ts`
- `frontend/src/types/paper.ts`
- `frontend/src/utils/filters.ts`

### Step 5 — Check each file for violations

For each file, check:

1. **Wrong-level imports** — does an atom import a molecule? does a molecule import an organism?
2. **Data-fetching in atoms/molecules** — `fetch`, `axios`, React Query calls belong in pages/organisms/hooks
3. **Business logic in templates** — templates must be dumb layout scaffolds
4. **`app/` vs `pages/` duplication** — if both `app/map/page.tsx` and `pages/MapPage.tsx` exist, check whether `app/` is a thin wrapper; if it duplicates logic, flag it
5. **React imports in utils/services** — `services/` must be pure; `utils/` must be pure
6. **Missing component boundaries** — a single file doing atom + molecule + organism work
7. **Dead exports** — components defined but never imported anywhere

---

## Step 6 — Write `docs/infrastructure-review.md`

Create `docs/` if it does not exist. Write the report using this structure:

```markdown
# Infrastructure Review — Chilean Marine Seismic Lines

_Reviewed: YYYY-MM-DD_

## Executive Summary

[2–4 sentences: overall health, number of violations by severity, top concern]

---

## Backend — Hexagonal Architecture

### Dependency Graph (as-found)

[ASCII diagram showing actual imports between layers]

### Violations

| # | File | Severity | Rule violated | Description | Fix |
|---|------|----------|---------------|-------------|-----|
| 1 | api/routers/papers.py | CRITICAL | api→infrastructure forbidden | Directly imports JsonRepository | Inject via dependencies.py |
| … | … | … | … | … | … |

### Clean files

[List files with no violations]

---

## Frontend — Atomic Design

### Component Tree (as-found)

[ASCII diagram showing which files import which]

### Violations

| # | File | Severity | Rule violated | Description | Fix |
|---|------|----------|---------------|-------------|-----|
| 1 | atoms/MetricCard.tsx | WARNING | Atom fetches data | Calls api.ts directly | Accept data as prop; move fetch to parent organism |
| … | … | … | … | … | … |

### Clean files

[List files with no violations]

---

## Priority Fix List

Ordered by impact:

1. **[CRITICAL]** … — _one sentence why urgent_
2. **[WARNING]** … — _one sentence why it matters_
3. …

---

## Review Notes

_YYYY-MM-DD: [Any observations about architectural drift or open questions]_
```

**Rules for updating (when re-run):**
- Never remove existing violations — mark them `resolved` with a date if fixed
- Add a new `Review Notes` entry for each run
- Keep violation IDs stable across runs

---

## Step 7 — Print summary to user

After writing the file, output:
- Total violations found (CRITICAL / WARNING / INFO counts) for backend and frontend separately
- Top 3 fixes to tackle first
- Any file that is completely clean (praise it)
- If `$ARGUMENTS` is provided (e.g., `/infrastructure-reviewer backend`), limit the audit to that layer only