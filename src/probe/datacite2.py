"""DataCite with correct PANGAEA client ID."""
import requests, re, sys, json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent.parent

H = {"User-Agent": "Mozilla/5.0"}

# Try correct client ID: pangaea.repository
for cruise, extra in [
    ("SO181", "TIPTEQ seismic Chile"),
    ("SO161", "SPOC seismic Chile"),
    ("SO104", "CINCA seismic Chile"),
    ("SO210", "Chile seismic"),
    ("SO244", "Chile seismic"),
]:
    url = (f"https://api.datacite.org/dois"
           f"?query={requests.utils.quote(cruise + ' ' + extra)}"
           f"&client-id=pangaea.repository"
           f"&page[size]=10")
    r = requests.get(url, headers=H, timeout=20)
    d = r.json()
    total = d.get("meta", {}).get("total", 0)
    print(f"\n{cruise} + '{extra}': total={total}")
    for item in d.get("data", [])[:5]:
        attrs = item.get("attributes", {})
        doi = attrs.get("doi", "")
        title = (attrs.get("titles") or [{}])[0].get("title", "")
        print(f"  {doi:45s} {title[:65]}")

# Also try just the cruise name
print("\n=== Just cruise name ===")
for cruise in ["SO104", "SO181", "SO161", "JC23", "SO210"]:
    url = (f"https://api.datacite.org/dois"
           f"?query={cruise}"
           f"&client-id=pangaea.repository"
           f"&page[size]=5")
    r = requests.get(url, headers=H, timeout=20)
    d = r.json()
    total = d.get("meta", {}).get("total", 0)
    print(f"{cruise}: total={total}")
    for item in d.get("data", [])[:3]:
        attrs = item.get("attributes", {})
        doi = attrs.get("doi", "")
        title = (attrs.get("titles") or [{}])[0].get("title", "")
        print(f"  {doi:45s} {title[:60]}")
