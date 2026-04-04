# Paper Analyzer — Chilean Marine Seismic Lines

You are an expert geophysicist and data scientist specializing in marine seismic surveys. Your job is to deeply analyze each paper from `papers/survey_results.json`, extract structured metadata, locate raw/processed data sources, and produce one JSON file per paper.

## Input

Read `papers/survey_results.json`. Process all papers with `"status": "TO_ANALYZE"`.

If a specific paper ID or URL is passed as an argument (`$ARGUMENTS`), process only that paper.

## IMPORTANT — Write as you go

**After completing analysis of each individual paper, immediately write its JSON file to disk before moving to the next paper.** Do not batch up results. This ensures progress is preserved even if interrupted. Also immediately update that paper's `status` in `survey_results.json` to `"ANALYZED"` after writing its file.

## For each paper

### Step 1 — Fetch and read the paper

Use WebFetch on the paper URL. If behind a paywall, use the DOI resolver (`https://doi.org/{doi}`) and also try:
- Unpaywall (`https://api.unpaywall.org/v2/{doi}?email=research@example.com`)
- Semantic Scholar (`https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}`)
- OpenAlex (`https://api.openalex.org/works/doi:{doi}`)

Extract: abstract, methods section, data section, acknowledgments, references to datasets.

### Step 2 — Extract geographic information

Identify all marine seismic lines described in the paper:
- Survey area bounding box (lat/lon)
- Named locations (cities, bays, basins, fjords)
- Specific line names/codes (e.g., "Line SCS-1", "Profile P1")
- Convert any degree-minute-second coordinates to decimal degrees
- Assign a representative `latitude` and `longitude` (centroid of survey area)
- Nearest Chilean city for reference

### Step 3 — Identify data sources

Search for data links inside and outside the paper:
- Links mentioned in text (data availability statements, supplementary material)
- PANGAEA: search `https://pangaea.de/search?q={paper_title_keywords}`
- IRIS DMC / EarthScope: `https://ds.iris.edu/ds/nodes/dmc/` (OBS/seismometer networks)
- MGDS (Marine Geoscience Data System): `https://www.marine-geo.org/tools/search/entry.php?id={cruise_id}` if a cruise ID is mentioned
- RVData: `https://www.rvdata.us/search/cruise/{cruise_id}` for vessel cruise data
- SIOSEIS / USGS / NOAA repositories
- CONICYT / ANID data portals
- Any `ftp://` or `http://` data download links in the paper

For **each** of the following data types, create a separate entry in the `data` array (even if the URL is null — still record the type with `access: "unknown"` if you cannot confirm):

| data_type | Typical classification | Typical format | Where to look |
|---|---|---|---|
| `seismic_reflection_mcs` | PROCESSED (or SEMI_PROCESSED for stacks) | SEG-Y | MGDS, PANGAEA, journal supplement |
| `seismic_refraction_obs` | RAW or PROCESSED | SEG-Y, MSEED | IRIS/EarthScope, MGDS |
| `obh` | RAW or PROCESSED | SEG-Y, MSEED | IRIS/EarthScope, MGDS — Ocean Bottom Hydrophone data (pressure-only OBS) |
| `bathymetry` | RAW | NetCDF, XYZ, GMT | MGDS/RVData, NOAA NCEI |
| `backscatter` | RAW | GeoTIFF, NetCDF | MGDS/RVData |
| `gravity` | RAW | ASCII/CSV | MGDS/RVData, BGS, NOAA |
| `magnetics` | RAW | ASCII/CSV | MGDS/RVData, NOAA |
| `navigation` | RAW | CSV, NMEA, P190 | MGDS/RVData |
| `subbottom` | RAW | SEG-Y | MGDS/RVData — sub-bottom profiler (Knudsen, SBP, Parasound) |
| `velocity_sound` | RAW or PROCESSED | ASCII/CSV, NetCDF | CTD casts, XBT drops, PANGAEA — sound velocity profiles used for streamer/OBS geometry corrections |

Only include types that are plausibly acquired during the cruise described in the paper. For example: a pure OBS refraction paper likely has no MCS streamer data; a multichannel reflection paper may or may not have OBS.

### Step 4 — Classify data

**Access rule:** If a dataset has a URL pointing to a publicly reachable data hub (marine-geo.org, rvdata.us, iris.edu / earthscope.org, pangaea.de, noaa.gov, ngdc.noaa.gov, etc.), set `"access": "open"` — even if the hub page labels it "restricted". Reachable = available. Only set `"access": "restricted"` when the data requires institutional credentials or a formal access request with no public portal. Set `"access": "unknown"` only when you cannot find any link and cannot determine availability.

For each data source found, classify it:

- **RAW**: Original field recordings. SEG-D, SEG-Y (unprocessed), UKOOA P1/90 navigation files. No corrections applied beyond demux.
- **SEMI_PROCESSED**: Gain corrections, geometry assignment, stacking velocity analysis applied. Stacked sections. May include NMO, DMO. Interpretable but not migrated.
- **PROCESSED**: Full processing sequence complete — migration (PSTM/PSDM), multiple suppression, final interpretation-ready sections. Also includes derived products like velocity models, depth sections, interpreted horizons.

### Step 5 — Describe processing

Summarize the processing workflow described in the paper:
- Acquisition parameters (vessel, source type, streamer length, channel count, sample rate)
- Processing sequence (list the steps in order)
- Software used (if mentioned)
- Key parameters (migration aperture, velocity model type, etc.)

## Output format

Save to `papers/{paper_id}.json`:

```json
{
  "id": "author_year_keyword",
  "title": "Full paper title",
  "authors": ["Last, First"],
  "year": 2020,
  "journal": "Journal name",
  "doi": "10.xxxx/...",
  "url": "https://...",
  "open_access_url": "https://... or null",
  "abstract": "Full abstract text",
  "keywords": ["keyword1", "keyword2"],

  "location": {
    "latitude": -33.45,
    "longitude": -71.62,
    "city": "Valparaíso",
    "region": "Región de Valparaíso",
    "country": "Chile",
    "description": "Offshore Valparaíso, central Chilean margin",
    "bounding_box": {
      "lat_min": -34.0, "lat_max": -33.0,
      "lon_min": -72.5, "lon_max": -71.0
    },
    "seismic_lines": [
      {
        "name": "Line SCS-1",
        "lat_start": -33.2, "lon_start": -71.8,
        "lat_end": -33.6, "lon_end": -72.1,
        "length_km": 45
      }
    ]
  },

  "acquisition": {
    "vessel": "R/V Name or unknown",
    "year_acquired": 2015,
    "source_type": "airgun array / sparker / water gun",
    "source_volume_cui": 5000,
    "streamer_length_m": 6000,
    "channel_count": 480,
    "sample_rate_ms": 2,
    "record_length_s": 14,
    "fold": 120,
    "line_spacing_km": null
  },

  "data": [
    {
      "data_type": "seismic_reflection_mcs | seismic_refraction_obs | bathymetry | backscatter | gravity | magnetics | navigation | subbottom",
      "name": "Human-readable name, e.g. 'MGL1610 MCS Reflection Data'",
      "classification": "RAW | SEMI_PROCESSED | PROCESSED",
      "format": "SEG-Y | NetCDF | HDF5 | ASCII | CSV | GeoTIFF | MSEED | other",
      "url": "https://... or null",
      "doi": "10.xxxx/... or null",
      "repository": "MGDS | IRIS | PANGAEA | NOAA | RVData | CONICYT | journal_supplement | other",
      "size_gb": null,
      "access": "open | restricted | embargoed | unknown",
      "download_command": "wget -O filename 'https://...' or null",
      "description": "What this dataset contains and how it was used in the paper"
    }
  ],
  "_data_note": "Create one entry per data_type acquired during the cruise. Include all types plausibly available (seismic_reflection_mcs, seismic_refraction_obs, bathymetry, gravity, magnetics, navigation, etc.). Set url=null and access='unknown' for types you cannot confirm, rather than omitting them.",

  "processing": {
    "classification": "RAW | SEMI_PROCESSED | PROCESSED",
    "summary": "One-paragraph summary of the data state and processing applied",
    "workflow": [
      "1. Demultiplexing",
      "2. Geometry assignment",
      "3. Bandpass filter 5-8-80-100 Hz",
      "4. Velocity analysis every 500 CDP",
      "5. NMO correction",
      "6. CDP stack",
      "7. Post-stack time migration (Stolt, Vint)"
    ],
    "software": ["ProMAX", "SeisWare", "SeiSee"],
    "notes": "Any additional processing remarks"
  },

  "analyzed_at": "ISO-8601 timestamp",
  "analysis_confidence": "high | medium | low",
  "analysis_notes": "Notes about what could not be determined or was ambiguous"
}
```

## After processing all papers

Update each paper's `status` in `papers/survey_results.json` from `"TO_ANALYZE"` to `"ANALYZED"`.

Print a summary:
- How many papers analyzed
- How many with open data found
- Data classification breakdown (RAW / SEMI_PROCESSED / PROCESSED counts)
