# PDF → JSON Validator — Chilean Marine Seismic Lines

Validate a paper's JSON metadata against its actual PDF, correct any discrepancies, and record the result in `pdf_validation.json`.

## Input

If `$ARGUMENTS` is provided, treat it as the paper ID (e.g., `ramos_2018_tipteq_reflection_tecto`).

If no argument is given, open `pdf_validation.json` and pick the first entry where `"validated": false` and `"pdf_file"` is not null.

## Step 1 — Load current state

Read both files in parallel:
- `papers/{paper_id}.json`
- `pdf_validation.json`

Note the PDF path from `pdf_validation.json["papers"][*]["pdf_file"]` for this paper.

## Step 2 — Read the PDF

Read the PDF at the path noted above. If the file is large, read it in focused page ranges:
- Pages 1–3: title, authors, abstract, journal/year, DOI
- Look for: Methods / Data Acquisition / Instrumentation section (usually pages 3–8)
- Look for: Data Availability statement (often last 1–2 pages)
- Look for: Acknowledgments (cruise IDs, vessel names, funding)

## Step 3 — Validate these fields (in order of importance)

For each field, note what the JSON says vs. what the PDF says.

### Bibliographic
- `title` — exact title match
- `authors` — full author list in order (Last, First format); watch for missing or extra authors
- `year` — publication year
- `doi` — verify against paper header/footer; check for typos
- `open_access_url` — does the paper have a CC license or OA statement? If yes and `open_access_url` is null, find/set the URL.

### Geographic
- `bounding_box` — lat/lon extent of the survey area; expand if the PDF shows a wider range
- `seismic_lines` — named profiles, transects, line codes from figures/tables

### Acquisition
- `vessel` — exact vessel name(s) and cruise ID(s) (e.g., "R/V SONNE SO104")
- `year_acquired` — when the data was collected (may differ from publication year)
- `source_type` — airgun array / OBS / passive / sparker / sub-bottom profiler
- `source_volume_cui` — total air gun volume in cubic inches (convert from litres: 1 L ≈ 61.02 cui)
- `streamer_length_m` — hydrophone streamer length in metres
- `channel_count` — number of channels (= streamer_length_m / group_spacing_m if not stated directly)
- `sample_rate_ms` — sampling interval in milliseconds
- `record_length_s` — record length in seconds
- `fold` — nominal CDP fold

### Data
For each entry in `data[]`:
- `url` and `doi` — check the paper's Data Availability section for PANGAEA, MGDS, IRIS, or other repository links
- `access` — if a public URL exists, set `"open"`; if behind institutional login, `"restricted"`; otherwise `"unknown"`
- `format` — SEG-Y, NetCDF, miniSEED, etc. — correct if wrong for the data type
- `repository` — PANGAEA, MGDS, IRIS/EarthScope, RVData, NOAA, journal_supplement, etc.

### Processing
- `software` — exact software names mentioned (ProMAX, Claritas, SeisUNIX, GMT, SIMULPS, etc.)
- `workflow` — ordered processing steps; update/expand from the Methods section
- `classification` — RAW / SEMI_PROCESSED / PROCESSED

## Step 4 — Apply corrections

Edit `papers/{paper_id}.json` with all corrections found. Only change fields where the PDF contradicts the JSON. Do not rewrite fields that are already accurate.

Update `analysis_confidence`:
- `"high"` if the PDF was fully readable and key fields confirmed
- `"medium"` if some fields could not be verified (e.g., data URLs not in paper)
- `"low"` if PDF was inaccessible or key sections were missing

Update `analysis_notes` to summarize what was corrected and what remains uncertain.

## Step 5 — Update pdf_validation.json

Find the entry for this paper ID in `pdf_validation.json` and set:

```json
{
  "validated": true,
  "validated_at": "YYYY-MM-DD",
  "notes": "Brief summary of what was corrected: e.g. 'Fixed author list, added source_volume_cui=3124, corrected PANGAEA DOI'"
}
```

If the PDF was unreadable (too large, corrupted, or wrong paper), set:
```json
{
  "validated": false,
  "notes": "Reason: PDF too large / wrong paper / file missing"
}
```

## Step 6 — Report

Print a concise summary:
- Paper ID and title
- Fields corrected (list each one: old value → new value)
- Fields confirmed correct (list)
- Fields that could not be verified (list with reason)
- Any data URLs found or updated
