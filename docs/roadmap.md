# Project Roadmap — Chilean Marine Seismic Lines

_Last reviewed: 2026-04-03_

---

## Project Vision

Become the definitive open reference for marine seismic survey data along the Chilean subduction zone — a citable, interactive database that geophysicists worldwide can use to discover, compare, and download datasets without manually hunting through dozens of repositories. Within 1–2 years the project should have a stable DOI, draw seismic lines on the map, allow full-text search, and expose a GeoJSON/CSV API for downstream GIS workflows.

---

## Current State Summary

- **Papers catalogued:** 98 total — all with structured JSON metadata
- **Open-access datasets:** 113 datasets across 41 papers (42% of papers have downloadable data)
- **Restricted datasets:** 25 | **Unknown access:** 72 (many resolvable)
- **Data types covered:** MCS reflection (68), bathymetry (44), OBS refraction (43), gravity (15), navigation (15), sub-bottom (12), magnetics (8), OBH (3)
- **App features:** Interactive Leaflet map (React-Leaflet), table view, per-paper detail panel, filters by region / year / access / classification / data type, CSV export — served by a Next.js 14 frontend backed by a FastAPI REST API
- **Downloader:** CLI with `--all`, `--paper`, `--region`, `--classification`, `--dry-run` flags
- **Known gaps:**
  - No text search (title, author, keyword, cruise ID, line name)
  - No vessel/cruise filter — vessel field in JSONs is inconsistent (76 "unique" entries, many are compound descriptions like "Multiple GEOMAR cruises...")
  - Map shows only centroid dots — seismic lines have start/end coordinates but are not drawn
  - 72 datasets with `access: unknown` — many are likely publicly reachable and unchecked
  - No BibTeX citation export
  - No GeoJSON/static export for GIS tools
  - No citable DOI for the database itself
  - No cross-paper comparison or geographic clustering view

---

## Feature Backlog

### P1 — Do Next

_All P1 items completed — see Completed section._

### P2 — Planned

| ID | Feature | Category | Effort | Status | Notes |
|----|---------|----------|--------|--------|-------|
| F006 | **GeoJSON export of all survey lines** | download | medium | open | Add a `GET /papers/export/geojson` endpoint and generate a static `docs/chilean_seismic_lines.geojson` (updated via script) with one Feature per seismic line, properties containing paper ID, year, vessel, access status. Lets QGIS/ArcGIS users import the entire dataset directly. |
| F007 | **Vessel field normalization script** | data-quality | medium | open | Write a one-time `_normalize_vessels.py` script that maps the 76 inconsistent vessel strings to a canonical list (e.g., "R/V SONNE", "R/V Marcus G. Langseth", "R/V Conrad"). Patches all 98 JSONs in place. Prerequisite for F002 and for any cruise-based filtering. |
| F008 | **Resolve unknown-access datasets** | data-quality | medium | open | Write a `_check_access.py` script that iterates over all 72 `access: unknown` datasets, attempts a HEAD request to known public repos (marine-geo.org, rvdata.us, pangaea.de, iris.edu), and updates the JSON to `open` if the URL is reachable. Could surface ~20–30 additional open datasets. |
| F009 | **Survey line coverage heatmap** | visualization | medium | open | Add a "Coverage" page showing a density heatmap of seismic line coverage along the Chilean margin (count of lines per 0.5° grid cell). Back it with a `/stats/coverage` endpoint; render with React-Leaflet `HeatmapLayer` or a Recharts grid. Instantly reveals under-surveyed segments and is useful for proposals. |
| F010 | **Cross-paper comparison: geographic overlap** | discovery | medium | open | When a paper detail is open, show a "Nearby surveys" panel listing other papers whose bounding boxes overlap. Back it with a `/papers/{id}/nearby` endpoint. Enables researchers to find companion or competing datasets for the same region without manually scanning the map. |
| F011 | **Statistics dashboard page** | visualization | medium | open | Add an expanded "Stats" page with bar charts: papers per year, data types distribution, open vs restricted breakdown, vessel frequency, regional coverage. The `/stats` endpoint already exists — wire it up with Recharts. Replace the bare metric tiles on the current About page. |
| F012 | **Cruise ID as first-class field** | data-quality | medium | open | Add a `cruise_id` field to the JSON schema (e.g., "SO297", "MGL1701", "CINCA95") and backfill all 98 papers. Add cruise ID filter to the app. Many papers share cruise data; this creates a natural grouping that vessel name alone cannot provide. |

### P3 — Backlog

| ID | Feature | Category | Effort | Status | Notes |
|----|---------|----------|--------|--------|-------|
| F013 | **Zenodo citable dataset release** | community | large | open | Package the `papers/` directory as a versioned Zenodo deposit to get a DOI for the database itself. Add `CITATION.cff` and a `version` field to the schema. Enables the database to be cited in papers — the highest-leverage community feature. |
| F014 | **New paper alert automation** | automation | large | open | Write a script (or Claude slash command) that re-runs targeted searches on Google Scholar / OpenAlex / AGU journals for new papers since `survey_results.json.generated_at`. Outputs a list of candidate papers for manual review. Could be scheduled quarterly. |
| F015 | **Timeline animation: surveys by decade** | visualization | large | open | Add an animated slider to the map page that steps through decades (1987–1990s, 2000s, 2010s, 2020s) and shows how survey coverage grew. Good for talks and outreach. |
| F016 | **Per-paper related papers panel** | discovery | medium | open | Based on shared bounding box, vessel, or cruise, auto-generate a "Related papers" list for each detail panel. Lightweight version of F010 that doesn't require geographic overlap math — could be based on shared cruise_id (F012). |
| F017 | **Schema validation CI check** | infrastructure | small | open | Add a `validate_papers.py` script that checks all JSONs against the schema (required fields, valid enums, lat/lon ranges). Run it as a pre-commit hook or GitHub Action. Prevents schema drift as more papers are added. |
| F018 | **PDF viewer integration** | discovery | medium | open | The `pdfs/` directory exists — if a paper's PDF is present, serve it via a `/papers/{id}/pdf` endpoint and add a "View PDF" button in the detail panel that opens it inline (iframe or new tab). Reduces friction for researchers who want to read the paper alongside its metadata. |

---

## Completed

| ID | Feature | Completed |
|----|---------|-----------|
| I1 | **Backend PAPERS_DIR path fix** — `dependencies.py` now resolves the default papers path relative to the package root (`__file__.parents[4]`), not the CWD. Running `uvicorn` from `backend/` no longer fails to find `papers/`. | 2026-04-03 |
| I2 | **Remove orphaned Vite-era files** — deleted `frontend/src/App.tsx`, `src/main.tsx`, `vite.config.ts`, `src/pages/` (4 files + dir). These imported `react-router-dom` / `vite` (neither in `package.json`), causing TypeScript build errors. Project is now pure Next.js App Router. | 2026-04-03 |
| I3 | **Remove duplicate `index.css`** — deleted `frontend/src/index.css` (identical to `app/globals.css`; no longer imported now that `main.tsx` is gone). | 2026-04-03 |
| F001 | **Text search** — `q` query param on `GET /api/papers`; client-side filter across title, authors, keywords, city, journal; search input at top of FilterBar on map and database pages. | 2026-04-03 |
| F002 | **Vessel / cruise filter** — vessel SuggestInput already present in advanced filters; `applyFilters` handles partial match; vessels list built from `computeFilterOptions`. | 2026-04-03 |
| F003 | **Seismic lines on map** — `seismic_lines` added to `PaperSummarySchema`; React-Leaflet `Polyline` rendered per line with `showLines` toggle in map legend. | 2026-04-03 |
| F004 | **BibTeX citation export** — "Copy BibTeX" button in paper detail header; generates `@article{...}` from paper fields; copies to clipboard with 2-second confirmation. | 2026-04-03 |
| F005 | **Data completeness score** — 12-field completeness % computed as `Paper.completeness` property; exposed in both API schemas; colored badge in detail header and Fill% column in table. | 2026-04-03 |

---

## Review Notes

### 2026-04-03 — Initial review

**Audit findings:**
- All 98 papers have JSON files with rich metadata (locations, acquisition params, datasets). Data pipeline is mature and complete.
- The vessel field is the biggest data-quality debt: 76 "unique" values for what should be ~15–20 distinct vessels. F007 should be done before F002.
- 72 `unknown`-access datasets is an opportunity: many likely point to MGDS, PANGAEA, or RVData and could be upgraded to `open` automatically (F008).
- The seismic line coordinates are already in the data but invisible on the map — F003 is free value waiting to be unlocked.
- Tech stack is FastAPI (hexagonal architecture) + Next.js 14 / React-Leaflet / Recharts / Tailwind. Docker Compose handles local dev and production.
- The `download.py` CLI is solid. Main gap is no resume-on-error and no size-awareness.
- The project is 1–2 impactful features away from being shareable with the wider geophysics community (text search + line drawing + BibTeX = shareable today).
