"""
geofon.py — Scrape GEOFON network DOI pages for seismic dataset metadata.

For a given GEOFON network code + year, fetches:
  - Total data size (from DOI landing page, e.g. 507.3 GB)
  - Station list (via FDSN station service: count, lat/lon range, time range)
  - Channels and format (miniSEED)
  - License / access status

Uses the GEOFON FDSN station service, not WFcatalog, for station metadata.
WFcatalog is only needed if you want per-station size breakdown.

Usage:
    python -m src.scraper.geofon --doi 10.14470/mj7559637482
    python -m src.scraper.geofon --network ZW --year 2004
    python -m src.scraper.geofon --doi 10.14470/mj7559637482 --paper tilmann_2008_outer_rise_epsl
    python -m src.scraper.geofon --doi 10.14470/mj7559637482 --paper tilmann_2008_outer_rise_epsl --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PAPERS_DIR = Path(__file__).parent.parent.parent / "papers"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

GEOFON_BASE   = "https://geofon.gfz.de"
DATACITE_BASE = "https://api.datacite.org/dois"


# ── HTTP ──────────────────────────────────────────────────────────────────────

def get(url: str, timeout: int = 20) -> requests.Response:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            r.raise_for_status()
            return r
        except requests.RequestException as exc:
            if attempt == 2:
                raise
            print(f"  [retry {attempt+1}] {exc}", file=sys.stderr)
            time.sleep(2)
    raise RuntimeError("unreachable")


# ── Resolve DOI → network + year ─────────────────────────────────────────────

def resolve_doi(doi: str) -> tuple[str, str]:
    """Query DataCite for a GEOFON DOI and extract network code + year from URL."""
    doi = re.sub(r"^https?://doi\.org/", "", doi).strip()
    r = get(f"{DATACITE_BASE}/{doi}")
    attrs = r.json()["data"]["attributes"]
    url = attrs.get("url", "")
    # URL pattern: https://geofon.gfz.de/doi/network/{NET}/{YEAR}
    m = re.search(r"/doi/network/([^/]+)/(\d{4})", url)
    if not m:
        raise ValueError(f"Cannot extract network/year from DOI URL: {url}")
    return m.group(1), m.group(2)


# ── Parse GEOFON network DOI page ────────────────────────────────────────────

def parse_geofon_doi_page(network: str, year: str) -> dict:
    """
    Fetch the GEOFON network DOI landing page and extract:
      - total size (GB)
      - station count
      - time range
      - description / title
      - license / access
    """
    url = f"{GEOFON_BASE}/doi/network/{network}/{year}"
    print(f"  Fetching GEOFON page: {url}")
    r = get(url)
    html = r.text

    result: dict = {
        "geofon_url": url,
        "network_code": network,
        "year": year,
    }

    # Total size: e.g. "507.3GB" or "12.4 GB" or "230MB"
    size_m = re.search(r"([\d.]+)\s*(GB|MB|TB)", html)
    if size_m:
        num = float(size_m.group(1))
        unit = size_m.group(2).upper()
        if unit == "MB":
            num = round(num / 1024, 3)
        elif unit == "TB":
            num = round(num * 1024, 3)
        result["size_gb"] = num

    # License
    if re.search(r"creative\s*commons|cc.by|cc\s+by", html, re.I):
        result["access"] = "open"
    elif re.search(r"restricted|proprietary|not\s+publicly", html, re.I):
        result["access"] = "restricted"
    else:
        result["access"] = "open"  # GEOFON default after embargo

    return result


# ── FDSN station service ──────────────────────────────────────────────────────

def get_fdsn_stations(network: str, year: str) -> list[dict]:
    """
    Query GEOFON FDSN station service for all stations in network/year.
    Returns list of dicts with station code, lat, lon, start, end.
    """
    start = f"{year}-01-01"
    end   = str(int(year) + 2)  # give 2-year window for temporary nets
    fdsn_url = (
        f"{GEOFON_BASE}/fdsnws/station/1/query"
        f"?network={network}&starttime={start}&endtime={end}-01-01"
        f"&level=station&format=text"
    )
    print(f"  Fetching FDSN stations: {fdsn_url}")
    r = get(fdsn_url)
    stations = []
    for line in r.text.strip().splitlines():
        if line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 8:
            continue
        stations.append({
            "code":      parts[1],
            "latitude":  float(parts[2]),
            "longitude": float(parts[3]),
            "elevation": float(parts[4]),
            "start":     parts[6],
            "end":       parts[7],
        })
    return stations


# ── Build dataset entry ───────────────────────────────────────────────────────

def build_dataset_entry(doi: str, page: dict, stations: list[dict]) -> dict:
    """
    Combine DOI page metadata and FDSN station list into a paper JSON dataset entry.
    """
    n = len(stations)
    lats  = [s["latitude"]  for s in stations]
    lons  = [s["longitude"] for s in stations]
    starts = sorted(s["start"] for s in stations if s["start"])
    ends   = sorted(s["end"]   for s in stations if s["end"])

    lat_range = f"{min(lats):.2f}° to {max(lats):.2f}°" if lats else "?"
    lon_range = f"{min(lons):.2f}° to {max(lons):.2f}°" if lons else "?"
    date_start = starts[0][:10] if starts else "?"
    date_end   = ends[-1][:10]  if ends   else "?"

    net  = page["network_code"]
    year = page["year"]

    entry = {
        "data_type":      "seismic_refraction_obs",
        "name":           f"GEOFON network {net} ({year}) — {n} stations, {lat_range}",
        "classification": "RAW",
        "format":         ["miniSEED"],
        "url":            page["geofon_url"],
        "doi":            doi,
        "repository":     ["GFZ GEOFON"],
        "size_gb":        page.get("size_gb"),
        "access":         page.get("access", "open"),
        "download_command": (
            f"# FDSN mass downloader — network {net}\n"
            f"# obspy.clients.fdsn.mass_downloader, domain=RectangularDomain("
            f"minlatitude={min(lats):.1f}, maxlatitude={max(lats):.1f}, "
            f"minlongitude={min(lons):.1f}, maxlongitude={max(lons):.1f})"
        ) if lats else None,
        "description": (
            f"Temporary seismic network {net} deployed {date_start} – {date_end}, "
            f"{n} stations across {lat_range}, {lon_range}. "
            f"miniSEED waveforms archived at GEOFON."
        ),
        "cdp_spacing_m": None,
        # Extra provenance
        "_station_count": n,
        "_date_start":    date_start,
        "_date_end":      date_end,
    }
    return entry


# ── Patch paper JSON ──────────────────────────────────────────────────────────

def patch_paper(paper_id: str, new_entry: dict, dry_run: bool = False) -> None:
    path = PAPERS_DIR / f"{paper_id}.json"
    if not path.exists():
        print(f"  ERROR: {path} not found", file=sys.stderr)
        return

    paper = json.loads(path.read_text(encoding="utf-8"))
    existing = paper.get("data") or []

    # Dedup by DOI
    for d in existing:
        if d.get("doi") == new_entry["doi"]:
            print(f"  {paper_id}: DOI {new_entry['doi']} already present — skipping")
            return

    clean = {k: v for k, v in new_entry.items() if not k.startswith("_")}
    print(f"  {paper_id}: adding {clean['data_type']} [{clean.get('size_gb','?')} GB] (doi={clean['doi']})")

    if dry_run:
        print(f"    [dry-run] {json.dumps(clean, ensure_ascii=False)[:300]}")
        return

    paper["data"] = existing + [clean]
    path.write_text(json.dumps(paper, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Scrape a GEOFON network DOI for dataset metadata")
    ap.add_argument("--doi",     help="GEOFON DOI, e.g. 10.14470/mj7559637482")
    ap.add_argument("--network", help="FDSN network code, e.g. ZW")
    ap.add_argument("--year",    help="Network deployment year, e.g. 2004")
    ap.add_argument("--paper",   help="Paper ID to patch, e.g. tilmann_2008_outer_rise_epsl")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.doi and not (args.network and args.year):
        ap.error("Provide --doi OR both --network and --year")

    doi = args.doi or ""
    network = args.network or ""
    year    = args.year or ""

    if doi and not (network and year):
        print(f"Resolving DOI {doi} ...")
        network, year = resolve_doi(doi)
        print(f"  Network={network}  Year={year}")

    if not doi:
        doi = f"geofon:{network}/{year}"  # placeholder if no DOI provided

    page     = parse_geofon_doi_page(network, year)
    stations = get_fdsn_stations(network, year)

    print(f"  Stations: {len(stations)}  Size: {page.get('size_gb','?')} GB  Access: {page.get('access')}")

    entry = build_dataset_entry(doi, page, stations)

    print("\nDataset entry:")
    clean = {k: v for k, v in entry.items() if not k.startswith("_")}
    print(json.dumps(clean, indent=2, ensure_ascii=False))

    if args.paper:
        patch_paper(args.paper, entry, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
