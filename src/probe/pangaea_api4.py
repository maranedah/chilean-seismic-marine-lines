"""Try PANGAEA tab file for known DOI and OAI-PMH search."""
import requests, re, sys, json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent.parent

H = {"User-Agent": "Mozilla/5.0"}

# 1. Tab file of known SO104 DOI
print("=== PANGAEA.893034 tab header ===")
r = requests.get("https://doi.pangaea.de/10.1594/PANGAEA.893034?format=textfile", headers=H, timeout=20)
print(f"status={r.status_code} size={len(r.text)}")
lines = r.text.splitlines()
for i, l in enumerate(lines[:60]):
    print(f"{i:3d}: {l[:180]}")

# 2. Try PANGAEA OAI-PMH
print("\n=== OAI-PMH test ===")
oai = "https://ws.pangaea.de/oai/provider?verb=GetRecord&metadataPrefix=datacite4&identifier=oai:pangaea.de:doi:10.1594/PANGAEA.893034"
r2 = requests.get(oai, headers=H, timeout=20)
print(f"status={r2.status_code}")
print(r2.text[:2000])
