"""Comprehensive DataCite search using cruise IDs + campaign aliases + geophysical terms."""
import requests, re, sys, json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent.parent

H = {"User-Agent": "Mozilla/5.0"}

# cruise code -> [search terms to try]
SEARCHES = {
    "SO104":  ["SO104 Chile seismic bathymetry", "CINCA Chile seismic"],
    "SO107":  ["SO107 Chile", "SO107 Peru Chile trench"],
    "SO161":  ["SO161 Chile seismic", "SPOC Chile seismic", "SO161 SPOC"],
    "SO181":  ["SO181 Chile seismic", "TIPTEQ seismic", "SO181 TIPTEQ"],
    "SO210":  ["SO210 Chile seismic", "SO210 Maule"],
    "SO244":  ["SO244 Chile seismic bathymetry", "SO244 CINCA"],
    "SO297":  ["SO297 Chile seismic", "SO297 Copiapo"],
    "JC23":   ["JC23 Chile seismic OBS", "JC23 Maule"],
    "MR18-06":["MR18-06 Chile", "MR18 Chile triple junction OBS"],
}

GEOPHYS = ["seismic", "bathymetry", "multibeam", "gravity", "magnetic", "subbottom",
           "sub-bottom", "refraction", "reflection", "OBS", "OBH", "parasound", "chirp"]

found_dois: dict[str, dict] = {}  # doi -> info

for cruise, terms in SEARCHES.items():
    cruise_found = []
    for term in terms:
        url = (f"https://api.datacite.org/dois"
               f"?query={requests.utils.quote(term)}"
               f"&client-id=pangaea.repository"
               f"&page[size]=50")
        r = requests.get(url, headers=H, timeout=20)
        if r.status_code != 200:
            continue
        d = r.json()
        for item in d.get("data", []):
            attrs = item.get("attributes", {})
            doi = attrs.get("doi", "")
            if not doi or doi in found_dois:
                continue
            title = (attrs.get("titles") or [{}])[0].get("title", "")
            desc = " ".join(d.get("description","") for d in (attrs.get("descriptions") or []))
            subjects = " ".join(s.get("subject","") for s in (attrs.get("subjects") or []))
            combined = (title + " " + desc + " " + subjects).lower()
            # Must contain a geophysical term
            if any(g.lower() in combined for g in GEOPHYS):
                found_dois[doi] = {"cruise": cruise, "doi": doi, "title": title}
                cruise_found.append(doi)
    if cruise_found:
        print(f"\n{cruise}: {len(cruise_found)} geophysical datasets")
        for doi in cruise_found:
            print(f"  {doi:45s} {found_dois[doi]['title'][:65]}")
    else:
        print(f"{cruise}: 0")

print(f"\n\nTotal unique geophysical PANGAEA DOIs: {len(found_dois)}")
json.dump(list(found_dois.values()), open(ROOT / "_pangaea_found.json","w",encoding="utf-8"), indent=2)
print("Saved to _pangaea_found.json")
