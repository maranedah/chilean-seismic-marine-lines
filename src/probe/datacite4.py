"""Search cruise code only, paginate, filter geophysics locally."""
import requests, re, sys, json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent.parent

H = {"User-Agent": "Mozilla/5.0"}

GEOPHYS = re.compile(
    r'seismic|bathymetr|multibeam|gravit|magneti|sub.?bottom|parasound|chirp|'
    r'\bobs\b|\bobh\b|refraction|reflection|echo.?sounder|swath|subbottom',
    re.I
)

def get_all_pangaea(query: str, max_pages: int = 10):
    results = []
    url = (f"https://api.datacite.org/dois"
           f"?query={requests.utils.quote(query)}"
           f"&client-id=pangaea.repository"
           f"&page[size]=100&page[number]=1")
    for page in range(1, max_pages+1):
        r = requests.get(url, headers=H, timeout=20)
        if r.status_code != 200: break
        d = r.json()
        items = d.get("data", [])
        if not items: break
        results.extend(items)
        nxt = d.get("links", {}).get("next")
        if not nxt: break
        url = nxt
    return results

CRUISES = {
    "SO104": ["SO104"],
    "SO107": ["SO107"],
    "SO161": ["SO161"],
    "SO181": ["SO181", "TIPTEQ"],
    "SO210": ["SO210"],
    "SO244": ["SO244"],
    "SO297": ["SO297"],
    "JC23":  ["JC23"],
    "MR18-06": ["MR18-06", "MR1806"],
}

all_found = {}

for cruise, terms in CRUISES.items():
    cruise_hits = {}
    for term in terms:
        items = get_all_pangaea(term, max_pages=5)
        for item in items:
            attrs = item.get("attributes", {})
            doi = attrs.get("doi","")
            if not doi or doi in cruise_hits: continue
            title = (attrs.get("titles") or [{}])[0].get("title","")
            desc  = " ".join(d.get("description","") for d in (attrs.get("descriptions") or []))
            combined = title + " " + desc
            if GEOPHYS.search(combined):
                cruise_hits[doi] = {"cruise": cruise, "doi": doi, "title": title}

    if cruise_hits:
        print(f"\n{cruise}: {len(cruise_hits)} geophysical datasets")
        for doi, info in sorted(cruise_hits.items()):
            print(f"  {doi:45s}  {info['title'][:65]}")
    else:
        print(f"{cruise}: 0")
    all_found.update(cruise_hits)

print(f"\nTotal: {len(all_found)} unique geophysical PANGAEA DOIs")
json.dump(list(all_found.values()), open(ROOT / "_pangaea_found.json","w",encoding="utf-8"),
          indent=2, ensure_ascii=False)
print("Saved to _pangaea_found.json")
