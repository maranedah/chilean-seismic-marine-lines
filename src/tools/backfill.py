import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
PAPERS_DIR = ROOT / "papers"
EXCLUDE = {"survey_results.json", "data_availability.json", "schema.json"}

RULES = [
    ("seismic_refraction_obs", ["obs ", "obs/", "obs-", "wide-angle", "wide angle", "refraction obs", "seismic refraction", "xw network", "obs data", "obs wide", "ocean bottom seismometer"]),
    ("obh", ["obh", "ocean bottom hydrophone"]),
    ("bathymetry", ["bathymetry", "multibeam", "swath", "em122", "em710", "em300", "bathym"]),
    ("backscatter", ["backscatter", "sidescan", "side-scan", "side scan"]),
    ("gravity", ["gravity", "gravimeter", "gravimetry", "bgm-3"]),
    ("magnetics", ["magnetic", "magnetics", "g-882", "magnetometer"]),
    ("navigation", ["navigation", "positioning", "c-nav", "nmea", "p190", "p1/90", "shot time"]),
    ("subbottom", ["sub-bottom", "subbottom", "sbp", "knudsen", "parasound", "chirp"]),
    ("velocity_sound", ["sound velocity", "velocity profile", "svp", "ctd cast", "xbt", "sound speed"]),
    ("seismic_reflection_mcs", ["seismic reflection", "mcs", "multichannel", "multi-channel", "segd", "reflection data", "reflection profile", "shot data"]),
]

def infer_type(entry):
    text = " ".join([entry.get("name",""), entry.get("description",""), entry.get("format",""), entry.get("repository","")]).lower()
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

with open(ROOT / "_backfill_result.txt", "w") as f:
    f.write(f"Updated {changed} files\n")
