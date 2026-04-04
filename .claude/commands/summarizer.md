# Summarizer — Chilean Marine Seismic Lines

You are a scientific writer and geophysics expert. Your job is to read all analyzed paper JSON files from the `papers/` directory and produce a comprehensive, well-structured `README.md` at the project root.

## Input

Read all `.json` files in `papers/` directory (excluding `survey_results.json` and `schema.json`). Each file follows the paper schema with title, location, data classification, processing, etc.

## Output

Write `README.md` at the project root with the following structure:

---

```markdown
# Chilean Marine Seismic Lines — Paper Database

Brief 2-3 sentence description of the project: a curated database of scientific papers
about marine seismic surveys (reflection and refraction) along the Chilean coast and
offshore areas, including the subduction zone and continental margin.

## Overview

- Total papers: N
- Geographic coverage: [describe regions covered]
- Time span: [earliest year] – [latest year]
- Data availability: X open-access, Y restricted, Z unknown

## Papers by Geographic Region

Organize papers into sections by region (North Chile, Central Chile, South Chile, Full Coast).
For each region, list papers as a table:

| Title | Authors | Year | Location | Data Type | Data Status | Data Link |
|-------|---------|------|----------|-----------|-------------|-----------|
| [Title](url) | Author et al. | 2020 | Valparaíso | MCS Reflection | PROCESSED | [PANGAEA](url) |

## Papers Detail

For each paper, include a subsection:

### [Paper Title](url)

**Authors:** Author1, Author2  
**Year:** 2020  
**Journal:** Journal Name  
**DOI:** [10.xxxx/...](https://doi.org/10.xxxx/...)

**Location:** Latitude X°S, Longitude X°W — Nearest city, Region  
**Survey Area:** Brief description

**Seismic Lines:**
- Line Name: from (lat, lon) to (lat, lon), ~XX km

**Acquisition:**
- Vessel: R/V Name
- Source: type, volume
- Streamer: length, channels
- Year acquired: XXXX

**Data:**
| Dataset | Classification | Format | Access | Link |
|---------|---------------|--------|--------|------|
| MCS profiles | PROCESSED | SEG-Y | Open | [Download](url) |

**Processing Summary:**
Brief description of processing workflow.

**Processing Steps:**
1. Step 1
2. Step 2
...

---

## Data Download

All available datasets can be downloaded using the included `download.py` script:

```bash
# Download all open-access data
python download.py --all

# Download data for a specific paper
python download.py --paper author_year_keyword

# Download data classified as RAW only
python download.py --classification RAW

# Download to a specific directory
python download.py --all --output ./data/
```

Or use the web interface:
```bash
streamlit run app.py
```

## Interactive Web Interface

The `app.py` Streamlit application provides:
- Interactive map of all survey locations
- Filter by region, year, data type, classification
- Direct download links for all datasets
- Paper metadata viewer

## Data Classification Guide

- **RAW**: Original field recordings. SEG-D, unprocessed SEG-Y. Minimal corrections (demux, navigation merge).
- **SEMI_PROCESSED**: Geometry assigned, gain corrected, stacked but not migrated. Interpretable velocity sections.
- **PROCESSED**: Fully migrated (PSTM/PSDM), multiple-suppressed, interpretation-ready. May include depth conversion, interpreted horizons.

## Sources Checked

List all databases/repositories searched during the survey phase.

## Contributing

How to add new papers (point to schema.json as template).

## License

Data licenses vary by source. See individual paper JSON files for access and license details.
```

---

## Instructions

1. Read `papers/survey_results.json` for the list of sources checked
2. Read all `papers/*.json` (individual paper files)
3. Group papers by geographic region (infer from latitude/city)
4. Sort within each region by year (newest first)
5. Write a complete, publication-quality README.md
6. Make sure every URL in the README is the actual URL from the JSON (do not fabricate links)
7. If a paper has no data URL, write "Not publicly available" in the Data Link column
8. Include a final count of papers per classification at the end of the file

Save to `README.md` in the project root directory.
