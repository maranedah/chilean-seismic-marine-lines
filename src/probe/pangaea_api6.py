"""Try PANGAEA expedition/campaign pages and OAI-PMH sets for cruise IDs."""
import requests, re, sys, json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent.parent

H = {"User-Agent": "Mozilla/5.0"}

# 1. Check all OAI-PMH sets for cruise names
print("=== OAI-PMH sets containing SO ===")
r = requests.get("https://ws.pangaea.de/oai/provider?verb=ListSets", headers=H, timeout=20)
sets = re.findall(r'<setSpec>(.*?)</setSpec>', r.text)
so_sets = [s for s in sets if re.match(r'SO\d{2,3}', s, re.I)]
jc_sets = [s for s in sets if s.startswith("JC")]
print(f"SO sets ({len(so_sets)}): {so_sets[:30]}")
print(f"JC sets ({len(jc_sets)}): {jc_sets[:10]}")

target_sets = [s for s in sets if any(s.startswith(c) for c in
    ["SO104", "SO107", "SO161", "SO181", "SO210", "SO244", "SO297", "JC23", "MR18"])]
print(f"\nTarget cruise sets: {target_sets}")

# 2. Try PANGAEA expedition pages
for cruise in ["SO104", "SO161", "SO181", "SO210"]:
    for url_pat in [
        f"https://www.pangaea.de/expeditions/campaign/{cruise}",
        f"https://www.pangaea.de/?q={cruise}&topic=Geophysics",
        f"https://www.pangaea.de/expeditions/by-campaign/{cruise}",
    ]:
        r = requests.get(url_pat, headers=H, timeout=15)
        dois = re.findall(r'10\.1594/PANGAEA\.(\d+)', r.text)
        if dois:
            print(f"\n{url_pat}: found {len(set(dois))} DOIs")
            for d in sorted(set(dois))[:8]:
                print(f"  PANGAEA.{d}")
            break
        else:
            print(f"{url_pat}: {r.status_code}, no DOIs")
