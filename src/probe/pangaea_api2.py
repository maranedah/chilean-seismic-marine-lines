"""Check PANGAEA APIs and find correct query format for cruise search."""
import requests, json, re, sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent.parent

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

# 1. First look at the tab file of the known SO104 DOI to see the campaign field
print("=== SO104 known DOI tab header ===")
r = requests.get("https://doi.pangaea.de/10.1594/PANGAEA.893034?format=textfile", headers=HEADERS, timeout=20)
lines = r.text.splitlines()
for l in lines[:50]:
    if any(k in l for k in ["Citation", "Campaign", "Event", "License", "Abstract", "Keyword"]):
        print(repr(l[:200]))

print()

# 2. Try different PANGAEA search API formats
tests = [
    "https://ws.pangaea.de/es/pangaea/panmd/_search?q=campaign.name:SO104&size=5",
    "https://www.pangaea.de/search?q=campaign:SO104&count=5&format=json",
    "https://www.pangaea.de/search?q=%22SO104%22&count=5&format=json",
    "https://ws.pangaea.de/search/api/v1/datasets?query=SO104&limit=5",
]
for url in tests:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        print(f"GET {url}")
        print(f"  status={r.status_code}  content-type={r.headers.get('Content-Type','?')[:50]}")
        if r.status_code == 200:
            try:
                d = r.json()
                print(f"  JSON keys: {list(d.keys())[:8]}")
                # look for hits
                hits = d.get("hits", {}).get("hits", d.get("results", d.get("data", [])))
                if isinstance(hits, list):
                    print(f"  hits: {len(hits)}")
                    if hits:
                        print(f"  first: {json.dumps(hits[0])[:200]}")
            except Exception as e:
                print(f"  not JSON: {r.text[:200]}")
        print()
    except Exception as e:
        print(f"  ERROR: {e}\n")
