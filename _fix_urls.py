"""Fix search-page URLs in all paper JSONs.

Previous state: all cruise-level entry.php URLs were converted to PANGAEA
search queries (e.g. pangaea.de/search?q=SO161+SPOC...). Those are still
generic search pages, not direct dataset links.

This script replaces them with:
  - Real PANGAEA dataset DOIs where they exist (bathymetry compilations)
  - null + access=unknown for seismic/OBS data with no public dataset DOI
  - Specific MGDS Files.php dataset pages for MGL1701 / MGL1610 MCS data
"""

import json
from pathlib import Path

PAPERS_DIR = Path("papers")
EXCLUDE = {"survey_results.json", "data_availability.json", "schema.json"}

# Real PANGAEA dataset DOIs found via research
PANGAEA_SO104_BATHY = "https://doi.pangaea.de/10.1594/PANGAEA.893033"   # Geersen et al. 2018 multibeam (SO104+SO244+MGL1610)
PANGAEA_SO211_BATHY = "https://doi.pangaea.de/10.1594/PANGAEA.983166"   # Spieß et al. 2025 multibeam (SO211)

# Real MGDS dataset pages (specific dataset, not cruise entry)
MGDS_MGL1701_MCS = "https://www.marine-geo.org/tools/search/Files.php?data_set_uid=24399"
MGDS_MGL1701_MCS_DOI = "10.1594/IEDA/324399"
MGDS_MGL1610_MCS = "https://www.marine-geo.org/tools/search/Files.php?data_set_uid=23934"
MGDS_MGL1610_MCS_DOI = "10.1594/IEDA/323934"

report = []
total_fixed = 0
files_updated = 0


def fix_dataset(entry: dict) -> bool:
    """Apply URL fix to a single dataset entry. Returns True if modified."""
    url = entry.get("url") or ""
    dtype = entry.get("data_type", "")
    modified = False

    # ── SO104 / CINCA95 ──────────────────────────────────────────────────────
    if "pangaea.de/search?q=SO104" in url:
        if dtype == "bathymetry":
            entry["url"] = PANGAEA_SO104_BATHY
            entry["doi"] = "10.1594/PANGAEA.893033"
            entry["repository"] = "PANGAEA"
            entry["access"] = "open"
        else:
            entry["url"] = None
            entry["access"] = "unknown"
            entry["repository"] = "BGR / PANGAEA"
        modified = True

    # ── SO161 / SPOC ─────────────────────────────────────────────────────────
    elif "pangaea.de/search?q=SO161" in url:
        entry["url"] = None
        entry["access"] = "unknown"
        modified = True

    # ── SO181 / TIPTEQ ───────────────────────────────────────────────────────
    elif "pangaea.de/search?q=SO181" in url:
        entry["url"] = None
        entry["access"] = "unknown"
        modified = True

    # ── SO210 ─────────────────────────────────────────────────────────────────
    elif "pangaea.de/search?q=SO210" in url:
        entry["url"] = None
        entry["access"] = "unknown"
        modified = True

    # ── SO211 ─────────────────────────────────────────────────────────────────
    elif "pangaea.de/search?q=SO211" in url:
        if dtype == "bathymetry":
            entry["url"] = PANGAEA_SO211_BATHY
            entry["doi"] = "10.1594/PANGAEA.983166"
            entry["repository"] = "PANGAEA"
            entry["access"] = "open"
        else:
            entry["url"] = None
            entry["access"] = "unknown"
        modified = True

    # ── MGL1701 cruise entry → specific MCS dataset page ────────────────────
    elif "entry.php?id=MGL1701" in url:
        entry["url"] = MGDS_MGL1701_MCS
        entry["doi"] = MGDS_MGL1701_MCS_DOI
        entry["repository"] = "MGDS"
        entry["access"] = "open"
        modified = True

    # ── MGL1610 cruise entry → specific MCS dataset page ────────────────────
    elif "entry.php?id=MGL1610" in url:
        entry["url"] = MGDS_MGL1610_MCS
        entry["doi"] = MGDS_MGL1610_MCS_DOI
        entry["repository"] = "MGDS"
        entry["access"] = "open"
        modified = True

    return modified


for path in sorted(PAPERS_DIR.glob("*.json")):
    if path.name in EXCLUDE:
        continue
    data = json.loads(path.read_text(encoding="utf-8"))
    file_modified = False
    for entry in data.get("data", []):
        old_url = entry.get("url") or ""
        if fix_dataset(entry):
            file_modified = True
            total_fixed += 1
            report.append(f"  {path.stem}  [{entry['data_type']}]  {old_url[:70]}  →  {str(entry.get('url', 'null'))[:70]}")
    if file_modified:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        files_updated += 1

print(f"Files updated : {files_updated}")
print(f"Entries fixed : {total_fixed}")
print()
for line in report:
    print(line)
