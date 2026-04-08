"""
Find PANGAEA DOIs already in paper JSONs, and map cruise IDs to papers.
"""
import json, re, sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent.parent
PAPERS_DIR = ROOT / "papers"

# Cruises that 404'd on MGDS — likely PANGAEA (German/international vessels)
PANGAEA_CRUISES = ["SO104", "SO107", "SO161", "SO181", "SO210", "SO244", "SO297",
                   "JC23", "RC2901", "RC2902", "SO101", "SO103", "AT26-09",
                   "MR18-06", "IT95", "IT97"]

CRUISE_RE = re.compile(r'\b([A-Z]{1,4}\d{2,4}(?:-\d+)?)\b')

cruise_to_papers = {}
existing_pangaea = []  # papers already with PANGAEA dois

for f in sorted(PAPERS_DIR.glob("*.json")):
    if f.name in {"survey_results.json", "data_availability.json", "schema.json"}:
        continue
    p = json.loads(f.read_text(encoding="utf-8"))
    pid = p["id"]

    # Check existing data entries for PANGAEA
    for d in p.get("data") or []:
        doi = d.get("doi") or ""
        url = d.get("url") or ""
        if "PANGAEA" in doi or "pangaea" in url.lower():
            existing_pangaea.append({"paper": pid, "doi": doi, "url": url,
                                     "data_type": d.get("data_type")})

    # Extract cruise IDs
    sources = []
    acq = p.get("acquisition") or {}
    for exp in (acq.get("expeditions") or []):
        sources.append(exp)
    for kw in (p.get("keywords") or []):
        sources.append(kw)

    found = set()
    for s in sources:
        for cid in CRUISE_RE.findall(s):
            if re.match(r'^[NS]\d', cid): continue
            if re.match(r'^[A-Z]{2}', cid) and cid in PANGAEA_CRUISES:
                found.add(cid)

    for cid in found:
        cruise_to_papers.setdefault(cid, []).append(pid)

print("=== Existing PANGAEA DOIs in papers ===")
if existing_pangaea:
    for e in existing_pangaea:
        print(f"  {e['paper']:50s}  {e['data_type']:25s}  {e['doi']}")
else:
    print("  (none)")

print("\n=== Cruise -> Papers (PANGAEA candidates) ===")
for cid in sorted(cruise_to_papers):
    papers = cruise_to_papers[cid]
    print(f"\n  {cid} ({len(papers)} papers):")
    for pid in papers:
        print(f"    {pid}")

# Save for use by batch script
out = {"cruise_to_papers": cruise_to_papers}
(ROOT / "_pangaea_map.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print("\nSaved to _pangaea_map.json")
