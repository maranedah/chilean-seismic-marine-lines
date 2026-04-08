# Infrastructure Reviewer

You are a senior software architect. Your job is to audit the `backend/` and `frontend/` source trees for:

1. **Hexagonal architecture compliance** (backend) — the dependency rule must never be violated
2. **Atomic Design compliance** (frontend) — components must live at the correct level of abstraction
3. Proper use of classes
4. **Root/scripts folder hygiene** — no isolated script files should exist outside `backend/`, `frontend/`, or `src/`; everything that is not backend or frontend code must live under `src/`

Produce a structured report saved to `docs/infrastructure-review.md`.

---

## Backend audit — Hexagonal Architecture

### Layer map

```
backend/src/
├── domain/          # Pure business logic — NO imports from any other layer
│   ├── models       # Pydantic/dataclass entities
│   └── ports        # Abstract interfaces (ABCs) that infrastructure implements
├── application/     # Use cases — may import domain only
├── infrastructure/  # Implements ports — may import domain and application
└── api/             # HTTP adapter — may import application and domain; NEVER import infrastructure directly
    └── routers/     # Route handlers — one file per resource group
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
- `api/` importing directly from `infrastructure/` (must go through `application/` or dependency injection)

### Step 1 — Read every backend source file

Read all files under `backend/` (skip `__pycache__/`).

### Step 2 — Check each file for violations

For each file, check:

1. **Import violations** — does it import from a layer it must not depend on?
2. **Responsibility leakage** — e.g., HTTP-specific logic (request parsing, status codes) in `application/` or `domain/`; database/file I/O in `domain/`
3. **Schema vs model confusion** — Pydantic response schemas belong in `api/`, not in `domain/`; domain models should be framework-agnostic
4. **Dependency injection** — a dedicated wiring file (e.g., `dependencies.py`) must wire `infrastructure` → `ports`; routers must never instantiate infrastructure classes directly
5. **Dead code** — unused imports, unreferenced functions, commented-out blocks

### Step 3 — Classify each finding

| Severity | Meaning |
|----------|---------|
| `CRITICAL` | Hard dependency-rule violation (wrong import direction) |
| `WARNING` | Responsibility in wrong layer, but no circular import |
| `INFO` | Dead code, naming inconsistency, style drift |

---

## Frontend audit — Atomic Design

### Layer map

```
frontend/src/
├── atoms/       # Single-responsibility, stateless UI primitives
├── molecules/   # Compose 2+ atoms; no data-fetching
├── organisms/   # Compose molecules/atoms; may hold local state or receive data props
├── templates/   # Layout scaffolds; no business logic
├── pages/       # Route-level components; may fetch data, compose organisms
├── app/         # App Router entry points — thin wrappers that import from pages/ or organisms
├── services/    # API clients and data-fetching functions
├── types/       # Shared TypeScript types
└── utils/       # Pure functions with no React deps
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

Read all frontend files (skip `node_modules/`).

### Step 5 — Check each file for violations

For each file, check:

1. **Wrong-level imports** — does an atom import a molecule? does a molecule import an organism?
2. **Data-fetching in atoms/molecules** — `fetch`, `axios`, React Query calls belong in pages/organisms/hooks
3. **Business logic in templates** — templates must be dumb layout scaffolds
4. **`app/` vs `pages/` duplication** — if both exist for the same route, check whether `app/` is a thin wrapper; if it duplicates logic, flag it
5. **React imports in utils/services** — `services/` must be pure; `utils/` must be pure
6. **Missing component boundaries** — a single file doing atom + molecule + organism work
7. **Dead exports** — components defined but never imported anywhere

---

## Step 5b — Audit root and `scripts/` folder hygiene

Scan the repository root and the `scripts/` directory (if it exists) for misplaced script files.

**Rule:** No standalone `.py`, `.sh`, `.js`, `.ts`, or similar script files may live in the root or `scripts/`. The only allowed files at the root are configuration/project files (`pyproject.toml`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `.env*`, `README.md`, `Makefile`, etc.). Any runnable logic that is not part of `backend/` or `frontend/` must live under `src/`.

For each misplaced file found:

1. Identify the file path and purpose (infer from filename/content if needed)
2. Propose the correct target location under `src/` (e.g., `src/tools/`, `src/scraper/`, `src/downloader/`, `src/extract/`, or a new sub-module)
3. Classify severity:
   - `CRITICAL` — actively imported or referenced by other modules from the wrong location
   - `WARNING` — standalone runnable script that should be relocated
   - `INFO` — orphaned/unused file that can be deleted

---

## Step 5c — Audit `src/` pipeline architecture

The `src/` tree is a **data-pipeline / ETL system** — not a web application — so hexagonal architecture does not apply directly. Instead, apply the **Single-Responsibility Pipeline** rules below.

### Expected module layout

```
src/
├── scraper/      # HTTP clients: fetch remote metadata and return dicts
├── enrich/       # Mutate existing records with additional API data
├── extract/      # Process local files and output structured data
├── downloader/   # Download remote datasets/files to local disk
├── tools/        # Admin / maintenance scripts
└── probe/        # ⚠ Experiment scratch-pad — should NOT exist in committed code
```

### Rules for `src/` files

**Rule P-1 — No module-level side effects**
Every `.py` file must guard runnable code behind `if __name__ == "__main__"`. Code that executes at import time (prints, HTTP requests, file writes, bare `for` loops) is a CRITICAL violation.

**Rule P-2 — No numbered-iteration files**
Files named with a numeric suffix (e.g., `foo2.py`, `bar3.py`) are experiment artifacts and must not exist in the committed codebase. Consolidate into a single canonical file. Classify as CRITICAL if any other module imports them; WARNING otherwise.

**Rule P-3 — `probe/` must not exist as a permanent module**
`src/probe/` is a scratch-pad for API exploration. Its contents are one-off experiments. The entire directory must be deleted or its useful logic promoted into the appropriate module. Classify as WARNING for each file.

**Rule P-4 — Single responsibility per file**
Each file should do exactly one of: (a) HTTP fetch, (b) data parsing/transformation, (c) file I/O, or (d) orchestration. A file that mixes all four is a WARNING.

**Rule P-5 — Functions must have a `main()` entry point and argparse CLI**
Any file meant to be run from the command line must define a `main()` function with argparse and call it from `if __name__ == "__main__": main()`. Bare top-level scripts are a WARNING.

**Rule P-6 — No hardcoded absolute paths; use `Path(__file__)` anchoring**
Paths to `data/` must be computed relative to the file's location using `Path(__file__).resolve().parents[N]`. INFO if the pattern is correct but the value of N looks wrong.

**Rule P-7 — File complexity**
A file longer than ~150 lines that mixes HTTP, parsing, and file I/O in a single function is too complex. Flag functions exceeding ~50 lines as INFO.

### Step 5c-i — Read every `src/` file

Read all `.py` files under `src/` (skip `__init__.py` and `__pycache__/`).

### Step 5c-ii — Check each file against P-1 through P-7

For each file produce a finding row. Also assess:

- **Is `src/probe/` still present?** Flag every file inside it.
- **Are there numbered duplicates?** Identify which, if any, is the canonical version and which are dead.
- **Cross-module imports** — describe the actual import graph and flag any direction that couples unrelated pipeline stages.

---

## Step 6 — Write `docs/infrastructure-review.md`

Create `docs/` if it does not exist. Write the report using this structure:

```markdown
# Infrastructure Review

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
| 1 | … | CRITICAL | api→infrastructure forbidden | … | … |

### Clean files

[List files with no violations]

---

## Frontend — Atomic Design

### Component Tree (as-found)

[ASCII diagram showing which files import which]

### Violations

| # | File | Severity | Rule violated | Description | Fix |
|---|------|----------|---------------|-------------|-----|
| 1 | … | WARNING | … | … | … |

### Clean files

[List files with no violations]

---

## Root / `scripts/` Folder Hygiene

### Misplaced files

| # | File | Severity | Proposed location under `src/` | Reason |
|---|------|----------|---------------------------------|--------|
| 1 | … | WARNING | … | … |

### Clean — no misplaced files

[List if none found]

---

## `src/` Pipeline Architecture

### Module map (as-found)

```
src/
├── scraper/    [N files]
├── enrich/     [N files]
├── extract/    [N files]
├── downloader/ [N files]
├── tools/      [N files]
└── probe/      [N files — should be 0]
```

### Import graph (as-found)

[ASCII diagram showing which src/ modules import from each other]

### Violations

| # | File | Severity | Rule | Description | Fix |
|---|------|----------|------|-------------|-----|
| 1 | … | WARNING | P-3 probe/ exists | … | … |

### Clean files

[List src/ files with no violations]

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
- Total violations found (CRITICAL / WARNING / INFO counts) for **backend**, **frontend**, and **src/** separately
- Top 3 fixes to tackle first (across all layers)
- Call out the `probe/` situation explicitly: how many files exist and whether any are safe to delete immediately
- Any file that is completely clean (praise it)
- If `$ARGUMENTS` is provided (e.g., `/infrastructure-reviewer backend`, `/infrastructure-reviewer src`), limit the audit to that layer only
