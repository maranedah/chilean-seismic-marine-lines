# Chilean Marine Seismic Lines — Project Guide for Claude

## What This Project Is

A curated database of ~98 scientific papers about **marine seismic surveys** (reflection and refraction) along the Chilean subduction zone, from northern Chile (~18°S) to the southernmost tip (~57°S), spanning 1987–2025.

Each paper is stored as a structured JSON file in `papers/` containing:
- Full bibliographic metadata (DOI, URL, open-access URL)
- Geographic location and bounding box
- Seismic acquisition parameters (vessel, streamer length, source volume, etc.)
- Dataset links with access status (open / restricted / unknown)
- Processing workflow and software used

A **Streamlit web app** (`app.py`) provides an interactive map and table view of all papers. A **data downloader** (`download.py`) fetches open-access research datasets (SEG-Y, NetCDF, etc.) referenced in each paper.

---

## Project Structure

```
chilean-seismic-marine-lines/
├── papers/                  # One JSON file per paper + survey_results.json
├── app.py                   # Streamlit interactive map app
├── download.py              # Dataset downloader (seismic data, bathymetry, etc.)
├── requirements.txt         # Python dependencies
├── README.md                # Full paper table by region
└── .claude/
    ├── CLAUDE.md            # This file
    ├── commands/            # Custom Claude slash commands
    │   ├── paper-analyzer.md
    │   ├── summarizer.md
    │   └── survey-researcher.md
    └── settings.json
```

---

## How to Run

### Install dependencies
```bash
pip install -r requirements.txt
```

### Launch the Streamlit app
```bash
streamlit run app.py
```

### Download open-access datasets
```bash
python download.py --all               # all open-access datasets
python download.py --report            # show availability report
python download.py --paper bangs_2020_basal_accretion_jgr
python download.py --region "North Chile"
python download.py --all --dry-run     # preview without downloading
```

---

## Paper JSON Schema (key fields)

```json
{
  "id": "author_year_keyword_journal",
  "doi": "10.xxxx/...",
  "url": "https://...",
  "open_access_url": "https://... (direct PDF if open access, else null)",
  "data": [
    {
      "access": "open | restricted | unknown",
      "url": "direct dataset download URL or null",
      "classification": "RAW | SEMI_PROCESSED | PROCESSED"
    }
  ]
}
```

---

## Environment

This project is developed on **Windows**. Claude cannot see terminal output directly.

**Every shell command that produces output must redirect to a temp file, which Claude then reads and deletes:**

```bash
# Pattern to use for ALL commands with output
python some_script.py > _tmp_out.txt 2>&1
# Claude then reads _tmp_out.txt, then deletes it
```

```bash
# For inline one-liners
python -c "print('hello')" > _tmp_out.txt 2>&1
```

This applies to `python`, `pip`, `streamlit`, `curl`, and any other command whose output Claude needs to inspect. Never assume output appeared in the terminal — always write to a temp file first.