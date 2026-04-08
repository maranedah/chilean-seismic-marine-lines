"""Deeper probe: ES mapping, correct field names, and working search."""
import requests, json, sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent.parent

HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}

# 1. Check the known DOI
print("=== Known DOI 893034 ===")
r = requests.get("https://doi.pangaea.de/10.1594/PANGAEA.893034", headers=HEADERS, timeout=15)
print(f"status={r.status_code} url={r.url}")
# find campaign in JSON-LD
import re
ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', r.text, re.DOTALL)
if ld:
    try:
        d = json.loads(ld.group(1))
        print("JSON-LD keys:", list(d.keys()))
        print("campaign/event:", d.get("spatialCoverage"), d.get("temporalCoverage"))
        print("keywords:", d.get("keywords"))
        print("name:", d.get("name","")[:100])
    except: pass

# 2. Check ES index mapping for campaign fields
print("\n=== ES mapping for campaign ===")
r = requests.get("https://ws.pangaea.de/es/pangaea/panmd/_mapping", headers=HEADERS, timeout=15)
if r.status_code == 200:
    mapping = r.json()
    # find campaign-related fields
    props = mapping.get("pangaea", {}).get("mappings", {}).get("panmd", {}).get("properties",
            mapping.get("panmd", {}).get("mappings", {}).get("properties",
            mapping.get("mappings", {}).get("properties", {})))
    for k, v in props.items():
        if "campaign" in k.lower() or "cruise" in k.lower() or "basis" in k.lower():
            print(f"  {k}: {v}")
    # also show all top-level field names
    print("\n  Top-level fields:", sorted(props.keys())[:30])
else:
    print(f"mapping status: {r.status_code}")

# 3. Try a POST query
print("\n=== POST search for SO104 ===")
body = {
    "query": {"multi_match": {"query": "SO104", "fields": ["*"]}},
    "size": 5,
    "_source": ["URI", "title", "campaign", "keywords", "type"]
}
r = requests.post("https://ws.pangaea.de/es/pangaea/panmd/_search",
                  headers=HEADERS, json=body, timeout=15)
print(f"status={r.status_code}")
if r.status_code == 200:
    d = r.json()
    hits = d.get("hits", {}).get("hits", [])
    print(f"hits: {d['hits']['total']}")
    for h in hits:
        src = h.get("_source", {})
        print(f"  {src.get('URI','?'):40s} {src.get('title','?')[:60]}")
