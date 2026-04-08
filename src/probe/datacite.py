"""Use DataCite API to search for PANGAEA datasets by cruise and topic."""
import requests, re, sys, json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent.parent

H = {"User-Agent": "Mozilla/5.0"}

GEOPHYS_TERMS = ["seismic", "bathymetry", "multibeam", "gravity", "magnetic",
                 "subbottom", "sub-bottom", "refraction", "reflection", "OBS"]

def search_datacite(cruise: str, max_results: int = 200):
    """Search DataCite for PANGAEA datasets from a cruise, filtered to geophysics."""
    # DataCite API: filter by PANGAEA publisher and cruise name
    url = (
        f"https://api.datacite.org/dois"
        f"?query={requests.utils.quote(cruise)}"
        f"&client-id=awi.pangaea"
        f"&page[size]=100&page[number]=1"
    )
    results = []
    page = 1
    while len(results) < max_results:
        r = requests.get(url, headers=H, timeout=20)
        if r.status_code != 200:
            print(f"  DataCite error: {r.status_code}")
            break
        d = r.json()
        items = d.get("data", [])
        if not items:
            break
        for item in items:
            attrs = item.get("attributes", {})
            doi = attrs.get("doi", "")
            title = ""
            titles = attrs.get("titles", [])
            if titles:
                title = titles[0].get("title", "")
            # Filter to geophysical datasets
            combined = (title + " " + " ".join(
                s.get("subject","") for s in attrs.get("subjects",[])
            )).lower()
            if any(t.lower() in combined for t in GEOPHYS_TERMS):
                results.append({"doi": doi, "title": title})
        # Check pagination
        links = d.get("links", {})
        next_url = links.get("next")
        if not next_url or len(results) >= max_results:
            break
        url = next_url
        page += 1

    return results

# Test on key cruises
for cruise in ["SO104", "SO161", "SO181", "SO210", "SO244", "SO107", "SO297", "JC23"]:
    hits = search_datacite(cruise, max_results=100)
    print(f"\n{cruise}: {len(hits)} geophysical datasets")
    for h in hits[:10]:
        print(f"  {h['doi']:40s} {h['title'][:70]}")
    if len(hits) > 10:
        print(f"  ... and {len(hits)-10} more")
