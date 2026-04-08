# Data Quality Reviewer — Chilean Marine Seismic Lines

Audit all paper JSON files for data quality issues and apply fixes. Focus on field inconsistencies, duplicate variants, and normalization across the corpus.

## Input

If `$ARGUMENTS` is provided, treat it as a field name to audit (e.g., `vessel`, `software`, `repository`).

If no argument is given, run a full audit across all quality dimensions below.

## Step 1 — Extract field values

Run a Python script to extract all unique values for the target field across every `data/extracted_jsons/*.json` file (excluding `survey_results.json`). Count occurrences of each variant. Output: sorted frequency table.

Use the Windows temp-file pattern:
```bash
python -c "..." > _tmp_out.txt 2>&1
```

## Step 2 — Identify issues

For each field, look for:

### Vessel names
- **Incomplete names**: `R/V SONNE` with no cruise ID (20 bare entries is a sign of unvalidated papers)
- **Wrong full name**: `R/V Conrad` should be `R/V Robert Conrad`; `R/V James Cook` should be `RRS James Cook`
- **Variant spellings**: mixed case (`R/V Sonne` vs `R/V SONNE`), date format inconsistency (`Dec 2004–Feb 2005` vs `December 2004–February 2005`), slash style (`RC2901/RC2902` vs `RC2901, RC2902`)
- **Wrong year**: e.g. SO101 CONDOR was 1993, not 1995
- **Duplicate info**: same cruise described as `R/V L'Atalante (Bourgois et al.)` and `R/V L'Atalante (CTJ cruise, March–April 1997)`

### Software
- Mixed capitalisation: `GMT` vs `gmt`, `ProMAX` vs `Promax`
- Generic entries: `"unknown"` where a specific value is likely derivable
- Duplicate tools listed differently

### Repository
- Inconsistent names: `BGR / PANGAEA` vs `PANGAEA` vs `BGR`
- `IRIS DMC` vs `IRIS/EarthScope`

### Access
- Papers with a non-null `url` but `"access": "unknown"` (should be `"open"`)

## Step 3 — Build canonical mapping

For each group of variants, determine the canonical form:
- Prefer the most informative and most common form
- For vessel names: `R/V [Full Name] ([CruiseID], [Expedition], [Year])` format
- For software: match official product capitalisation
- For repositories: use the current official name

## Step 4 — Apply corrections

Edit each affected `data/extracted_jsons/{id}.json` file. Only change fields where a variant maps to the canonical form. Do not modify fields that are already canonical.

For vessel fields specifically, if a paper has `"R/V SONNE"` (bare, no cruise ID), do **not** guess the cruise ID — leave it and flag it for manual review instead.

## Step 5 — Report

Print a summary table:
```
FIELD        VARIANT                               → CANONICAL                              FILES CHANGED
vessel       R/V Conrad (RC2901, 1988)             → R/V Robert Conrad (RC2901, 1988)       3 files
vessel       R/V Sonne (SO181-1b, TIPTEQ, 2004)   → R/V SONNE (SO181, TIPTEQ, Dec 2004...  1 file
...
```

List any variants that could NOT be automatically resolved (need manual PDF check).

---

## Repository Scraping — Status & Findings

### Scrapers built

All scrapers live under `src/scraper/`. Run them with `python -m src.scraper.<module>`.

| Module | Covers | Status |
|--------|--------|--------|
| `src/scraper/mgds.py` | MGDS entry pages → R2R filesets → NCEI BagIt directories | Working |
| `src/scraper/mgds_batch.py` | Batch-patches 23 papers across 5 MGDS cruises (AT26-09, MGL1610, MGL1701, RC2901, RC2902) | Done |
| `src/scraper/pangaea.py` | PANGAEA tab file (`?format=textfile`) — parses metadata block, sums `Binary (Size)` column | Working |
| `src/scraper/pangaea_batch.py` | Batch-patches 26 dataset entries across 18 papers (SO104/SO244/SO297/JC23) | Done |
| `src/scraper/geofon.py` | GEOFON network DOI pages + FDSN station service — miniSEED waveform archives | Working |

### PANGAEA — verified DOI→paper mapping

Cruises covered: SO104, SO244, SO297, JC23. Excluded: SO107 (PANGAEA.931695 = Nicaragua), all SO161 datasets (foraminifera/radiocarbon — not geophysical).

Parent/collection DOIs (e.g. PANGAEA.893034) return HTTP 400 on `?format=textfile` — skip these; use their child DOIs instead.

### Repository reality check

| Repository label in JSONs | What it actually is | Scrapeable? | Notes |
|---|---|---|---|
| **MGDS** | Marine Geoscience Data System (`marine-geo.org`) | Yes — `scrape_cruise.py` | Entry page → R2R/NCEI filesets |
| **NOAA:NCEI** | NCEI BagIt archive (`ncei.noaa.gov/data/oceans/archive/`) | Yes — via MGDS scraper | `bag-info.txt` has DOI, size, license |
| **R2R** | Rolling Deck to Repository (`rvdata.us`) | Yes — via MGDS scraper | Redirects to NCEI; DOI = `10.7284/{fileset_id}` |
| **PANGAEA** | PANGAEA data publisher (`doi.pangaea.de`) | Yes — `scrape_pangaea.py` | Use DataCite API (`client-id=pangaea.repository`) to discover DOIs by cruise code |
| **GEOMAR OceanRep** | GEOMAR institutional publication archive (`oceanrep.geomar.de`) | **No** — not a data repo | Only holds PDFs of papers/cruise reports; raw data not deposited here. These entries have no real dataset URL. |
| **GFZ GEOFON** | GFZ waveform archive (`geofon.gfz.de`) | Yes — `scrape_geofon.py` | Landing page has total size as regex `[\d.]+\s*(GB\|MB)`; FDSN station service gives station count + bbox |
| **IRIS / FDSN** | FDSN seismological waveform archive (`service.iris.edu`) | Partial | Network codes needed; MEJIPE 8G_2013 lives here (restricted) |
| **GFZ DataServices** | GFZ Zenodo-based data deposits | Yes | Two OBS seismicity DBs: `10.5281/zenodo.10277799`, `10.5281/zenodo.10277798` |
| **BGR** | German Federal Institute for Geosciences (SO104/CINCA data) | **No** | No public data portal found; data appears to be internally archived |
| **LDEO** | Lamont-Doherty Earth Observatory (pre-2000 MCS) | **No** | Old ODP-era data; not publicly indexed |
| **SHOA** | Chilean Navy Hydrographic Service | **No** | No public data portal |
| **OGS** | Istituto Nazionale di Oceanografia, Trieste | Unknown | Not investigated |
| **internal / internal archive** | Author-held data, not deposited | **No** | By definition unreachable |

### GFZ GEOFON — known network DOIs

All discovered via DataCite search or `scrape_geofon.py --doi <doi>`. Scraper uses: (1) GEOFON DOI landing page for total size, (2) GEOFON FDSN station service for station count + bounding box.

| Network | DOI | Size | Stations | Lat range | Description | Papers patched |
|---------|-----|------|----------|-----------|-------------|----------------|
| ZW/2004 | `10.14470/mj7559637482` | 507.3 GB | 124 | -39.3° to -37.0° | TIPTEQ North (2004–2005), land broadband array | `tilmann_2008_outer_rise_epsl` |
| CX | `10.14470/pk615318` | — | 30 | -24.6° to -17.6° | IPOC permanent network, northern Chile | `reginato_2020_splay_fault_mejillones_tecto` (url+doi updated in-place) |
| 3D/2014 | `10.14470/8q7569558037` | 196 GB | 23 | -22.9° to -19.4° | HART-PISAGUA (2014 Iquique Mw 8.1 aftershocks) | — none matched (our papers use MCS/refraction, not aftershock seismicity) |
| IQ | `10.14470/vd070092` | — | 30 | -21.1° to -19.5° | Iquique Local Network + PicArray (2009–ongoing) | — not yet assigned |
| 8G_2013 | `10.7914/SN/8G_2013` | — | — | — | MEJIPE experiment, Mejillones 2013–2015 (restricted) | `reginato_2020_splay_fault_mejillones_tecto` (doi corrected from truncated `8G_201`) |

**Size not available** for CX and IQ: both are ongoing permanent networks; GEOFON landing page shows no total figure. Use WFcatalog API (`geofon.gfz.de/eidaws/wfcatalog/1/query`) per station if needed.

**TIPTEQ South**: no separate GEOFON DOI found — only the North array (ZW/2004) is registered. The South TIPTEQ data likely resides at GFZ Potsdam data services or is unpublished.

### Missing URLs — priority targets

As of 2026-04-06, entries still missing `url` and `doi`:
- **PANGAEA**: 38 entries — need to search DataCite by cruise code and verify geographic relevance
- **MGDS**: 32 entries — need to identify cruise IDs for papers not yet in `scrape_all_mgds.py`
- **GEOMAR OceanRep**: 17 entries — label is misleading; data not actually in OceanRep (see above)
- **BGR**: 12 entries — likely permanently restricted
- **LDEO**: 6 entries — likely not publicly accessible
- **IRIS**: 5 entries — need FDSN network codes per paper; queryable if known

### DataCite search pattern for PANGAEA cruises

```python
import requests
cruise = "SO297"  # just the cruise code, no extra terms
url = (f"https://api.datacite.org/dois"
       f"?query={requests.utils.quote(cruise)}"
       f"&client-id=pangaea.repository"
       f"&page[size]=100")
# Then filter locally with a GEOPHYS regex on title+description
# Manually verify borderline cases by checking Event(s) latitude in the tab file
```
