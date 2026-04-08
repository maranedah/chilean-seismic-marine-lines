"""Try PANGAEA search via HTML scraping + OAI-PMH campaign search."""
import requests, re, sys, json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent.parent

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 1. HTML search for SO104
for term in ["SO104", "campaign:SO104", "SO104 Chile seismic"]:
    url = f"https://www.pangaea.de/?q={requests.utils.quote(term)}&count=20"
    r = requests.get(url, headers=H, timeout=20)
    # Extract PANGAEA DOIs from HTML
    dois = re.findall(r'10\.1594/PANGAEA\.(\d+)', r.text)
    print(f"Search '{term}': {len(set(dois))} unique DOIs found")
    for d in sorted(set(dois))[:10]:
        print(f"  PANGAEA.{d}")
    print()

# 2. Check OAI-PMH ListIdentifiers for topicGeophysics
print("=== OAI-PMH ListIdentifiers topicGeophysics (first page) ===")
url = "https://ws.pangaea.de/oai/provider?verb=ListIdentifiers&metadataPrefix=datacite4&set=topicGeophysics"
r = requests.get(url, headers=H, timeout=20)
ids = re.findall(r'<identifier>(.*?)</identifier>', r.text)
token = re.search(r'<resumptionToken[^>]*>(.*?)</resumptionToken>', r.text)
print(f"  First page: {len(ids)} identifiers")
print(f"  Resumption token: {token.group(1)[:60] if token else 'None'}")
print(f"  Sample IDs:", ids[:5])

# 3. Try PANGAEA new API endpoint hints
for url in [
    "https://www.pangaea.de/api/datasets?q=SO104&topic=Geophysics&count=5",
    "https://ws.pangaea.de/oai/provider?verb=ListSets",
]:
    r = requests.get(url, headers=H, timeout=15)
    print(f"\nGET {url}")
    print(f"  status={r.status_code}")
    if r.status_code == 200 and len(r.text) < 5000:
        print(r.text[:1000])
    elif r.status_code == 200:
        # show sets
        sets = re.findall(r'<setSpec>(.*?)</setSpec>', r.text)
        print(f"  Sets: {sets[:20]}")
