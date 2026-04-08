"""
Find PANGAEA's actual search API by inspecting the page source,
and try DataCite with correct client ID.
"""
import requests, re, sys, json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent.parent

H = {"User-Agent": "Mozilla/5.0"}

# 1. Find API URLs in PANGAEA page source
r = requests.get("https://www.pangaea.de/", headers=H, timeout=20)
# Look for API/fetch calls
api_urls = re.findall(r'(?:fetch|ajax|axios|api)["\s:]*["\']([^"\']+?api[^"\']+)["\']', r.text, re.I)
print("API URLs in homepage source:")
for u in sorted(set(api_urls))[:20]:
    print(f"  {u}")

# Look for script src that might be the main bundle
scripts = re.findall(r'<script[^>]+src="([^"]+)"', r.text)
print("\nScript sources:")
for s in scripts[:10]:
    print(f"  {s}")

# 2. Check the correct PANGAEA client in DataCite
print("\n=== DataCite: PANGAEA clients ===")
r = requests.get("https://api.datacite.org/clients?query=pangaea&page[size]=10", headers=H, timeout=20)
if r.status_code == 200:
    d = r.json()
    for item in d.get("data", []):
        attrs = item.get("attributes", {})
        print(f"  id={item['id']:30s}  name={attrs.get('name','?')[:60]}")

# 3. Try DataCite DOI search with correct PANGAEA prefix
print("\n=== DataCite search for SO181 with PANGAEA prefix ===")
r = requests.get(
    "https://api.datacite.org/dois?query=SO181+seismic+Chile&prefix=10.1594&page[size]=5",
    headers=H, timeout=20
)
if r.status_code == 200:
    d = r.json()
    print(f"Total: {d.get('meta',{}).get('total',0)}")
    for item in d.get("data", [])[:5]:
        attrs = item.get("attributes", {})
        doi = attrs.get("doi", "")
        title = (attrs.get("titles") or [{}])[0].get("title", "")
        print(f"  {doi:45s}  {title[:60]}")

# 4. Try the PANGAEA catalog API (newer)
for url in [
    "https://ws.pangaea.de/pangaea-ws/catalog",
    "https://catalog.pangaea.de/api/datasets?q=SO181",
    "https://www.pangaea.de/geo/SciViews/SO181",
]:
    try:
        r = requests.get(url, headers=H, timeout=10)
        print(f"\n{url}: {r.status_code} {r.headers.get('Content-Type','')[:30]}")
        if r.status_code == 200 and "json" in r.headers.get("Content-Type",""):
            print(r.text[:300])
    except Exception as e:
        print(f"  ERROR: {e}")
