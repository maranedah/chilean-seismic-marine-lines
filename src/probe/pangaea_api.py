"""
Probe the PANGAEA API for cruise searches to understand response format
and dataset types available.
"""
import requests, json, re, sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent.parent

HEADERS = {"User-Agent": "Mozilla/5.0"}

def search(cruise: str, limit: int = 100):
    # PANGAEA elastic search API
    url = f"https://ws.pangaea.de/es/pangaea/panmd/_search?q=campaign.name:{cruise}&size={limit}"
    r = requests.get(url, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        # fallback: use the PANGAEA full-text search
        url2 = f"https://www.pangaea.de/api/finddata?term={cruise}&count={limit}&format=json"
        r = requests.get(url2, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            print(f"  {cruise}: both APIs failed ({r.status_code})")
            return []
        data = r.json()
        hits = data.get("results", [])
        return [{"doi": h.get("URI","").replace("https://doi.org/",""),
                 "title": h.get("citation",{}).get("title",""),
                 "source": "finddata"} for h in hits]

    data = r.json()
    hits = data.get("hits", {}).get("hits", [])
    results = []
    for h in hits:
        src = h.get("_source", {})
        doi = src.get("URI", "").replace("https://doi.org/", "")
        title = src.get("title", "")
        keywords = src.get("keywords", [])
        camp = src.get("campaign", {})
        results.append({"doi": doi, "title": title, "keywords": keywords,
                        "campaign": camp, "source": "es"})
    return results

# Test on key cruises
for cruise in ["SO104", "SO161", "SO181", "SO210", "SO244", "JC23", "SO297"]:
    print(f"\n=== {cruise} ===")
    hits = search(cruise, limit=200)
    print(f"  Total results: {len(hits)}")
    for h in hits[:20]:
        print(f"  {h['doi'][:35]:35s}  {h['title'][:80]}")
    if len(hits) > 20:
        print(f"  ... and {len(hits)-20} more")

# Save full results for SO104 and SO161 for inspection
for cruise in ["SO104", "SO161", "SO181"]:
    hits = search(cruise, limit=500)
    with open(ROOT / f"_pangaea_{cruise}.json", "w", encoding="utf-8") as f:
        json.dump(hits, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(hits)} results for {cruise} to _pangaea_{cruise}.json")
