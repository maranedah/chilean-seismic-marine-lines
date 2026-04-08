"""One-shot script: infer and backfill data_type on every data entry in papers/*.json

Usage:
    python -m src.tools.backfill_data_types
"""
import json, re
from pathlib import Path

PAPERS_DIR = Path(__file__).parent.parent.parent / "papers"
EXCLUDE = {"survey_results.json", "data_availability.json", "schema.json"}

RULES = [
    # (data_type,  list of case-insensitive substrings that trigger it)
    ("seismic_refraction_obs", ["obs ", "obs/", "obs-", "wide-angle", "wide angle", "refraction obs", "seismic refraction", "xw network", "obs data", "obs wide"]),
    ("obh",        ["obh"]),
    ("bathymetry", ["bathymetry", "multibeam", "swath", "em122", "em710", "bathym"]),
    ("backscatter",["backscatter", "sidescan", "side-scan", "side scan"]),
    ("gravity",    ["gravity", "gravimeter", "gravimetry", "bgm-3"]),
    ("magnetics",  ["magnetic", "magnetics", "g-882", "magnetometer"]),
    ("navigation", ["navigation", "positioning", "c-nav", "nmea", "p190", "p1/90"]),
    ("subbottom",  ["sub-bottom", "subbottom", "sbp", "knudsen", "parasound", "chirp"]),
    ("velocity_sound", ["sound velocity", "velocity profile", "svp", "ctd cast", "xbt", "sound speed"]),
    # MCS last so OBS/refraction rules above win for mixed entries
    ("seismic_reflection_mcs", ["seismic reflection", "mcs", "multichannel", "multi-channel", "segd", "reflection data", "reflection profile", "shot data"]),
]

def infer_type(entry: dict) -> str | None:
    text = " ".join([
        entry.get("name", ""),
        entry.get("description", ""),
        entry.get("format", ""),
        entry.get("repository", ""),
    ]).lower()
    for dtype, keywords in RULES:
        if any(kw in text for kw in keywords):
            return dtype
    return None

changed = 0
for path in sorted(PAPERS_DIR.glob("*.json")):
    if path.name in EXCLUDE:
        continue
    data = json.loads(path.read_text(encoding="utf-8"))
    modified = False
    for entry in data.get("data", []):
        if "_data_note" in entry:
            continue
        if not entry.get("data_type"):
            dtype = infer_type(entry)
            if dtype:
                entry["data_type"] = dtype
                modified = True
    if modified:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        changed += 1
        print(f"  updated {path.name}")

print(f"\nDone — {changed} files updated.")
