"""
mgds.py — Scrape MGDS cruise entry page + linked repositories
for dataset metadata, then optionally patch a paper JSON file.

Usage:
    python -m src.scraper.mgds --cruise MGL1701
    python -m src.scraper.mgds --cruise MGL1701 --paper bangs_2020_basal_accretion_jgr
    python -m src.scraper.mgds --cruise MGL1701 --dry-run
"""

from __future__ import annotations

import argparse
import html as html_module
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

import requests

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Constants ─────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

PAPERS_DIR = Path(__file__).parent.parent.parent / "data" / "extracted_jsons"

# Map MGDS data_type strings → our schema data_type values
DATA_TYPE_MAP = {
    "gravity:field":               "gravity",
    "gravity":                     "gravity",
    "magnetic:field":              "magnetics",
    "magnetics:field":             "magnetics",
    "magnetics":                   "magnetics",
    "navigation:primary":          "navigation",
    "navigation":                  "navigation",
    "seismic reflection/refraction": "seismic_reflection_mcs",
    "seismic:mcs":                 "seismic_reflection_mcs",
    "seismic:active:subbottom":    "subbottom",
    "subbottom":                   "subbottom",
    "temperature, velocity:sound": "velocity_sound",
    "velocity:sound":              "velocity_sound",
    "bathymetry":                  "bathymetry",
    "backscatter":                 "backscatter",
    "seismic:navigation":          "navigation",
}

# Map raw repository labels → clean names
REPO_MAP = {
    "noaa:ncei": "NOAA:NCEI",
    "r2r":       "R2R",
    "mgds":      "MGDS",
    "ieda":      "MGDS",
    "sesar":     "SESAR",
}


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def get(url: str, timeout: int = 20) -> requests.Response:
    """GET with retry and polite delay."""
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


def strip_tags(html: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def first(pattern: str, text: str, flags: int = 0) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


# ── MGDS entry page parser ────────────────────────────────────────────────────

def parse_mgds_entry(cruise_id: str) -> list[dict]:
    """
    Fetch https://www.marine-geo.org/tools/search/entry.php?id={cruise_id}
    and return a list of raw sensor dicts.
    """
    url = f"https://www.marine-geo.org/tools/search/entry.php?id={cruise_id}"
    print(f"Fetching MGDS entry: {url}")
    r = get(url)
    html = r.text

    rows = re.findall(
        r'<div class="filerow clickable">(.*?)<hr>', html, re.DOTALL
    )

    sensors = []
    for row in rows:
        dt_m = re.search(r'<span class="data_type">(.*?)</span>', row)
        if not dt_m:
            continue
        raw_type = strip_tags(dt_m.group(1)).strip()

        href_m = re.search(r'href="([^"]+)"', row)
        href = href_m.group(1) if href_m else None

        # All <span class="repository"> values — first is repo, second is format
        repo_spans = re.findall(r'<span class="repository">(.*?)</span>', row)
        repo_raw = repo_spans[0].strip() if len(repo_spans) > 0 else None
        fmt_raw  = repo_spans[1].strip() if len(repo_spans) > 1 else None

        # Investigators
        pis = re.findall(r'<div class="personname">(.*?)</div>', row)

        sensors.append({
            "raw_type": raw_type,
            "url": href,
            "repo_raw": repo_raw,
            "fmt_raw": fmt_raw,
            "pis": pis,
        })

    print(f"  Found {len(sensors)} sensor entries")
    return sensors


# ── R2R fileset page parser ───────────────────────────────────────────────────

def _parse_size(size_str: str) -> Optional[float]:
    """'152.6 MB' → 0.149, '1.2 GB' → 1.2, '253 MB' → 0.247"""
    m = re.match(r"([\d.]+)\s*(MB|GB|KB|TB)", size_str, re.I)
    if not m:
        return None
    val, unit = float(m.group(1)), m.group(2).upper()
    if unit == "KB":
        return round(val / 1024 / 1024, 4)
    if unit == "MB":
        return round(val / 1024, 4)
    if unit == "GB":
        return round(val, 3)
    if unit == "TB":
        return round(val * 1024, 1)
    return None


def parse_ncei_bagit_dir(ncei_url: str) -> dict:
    """
    Parse an NCEI R2R BagIt directory (e.g. /arc0131/{accession}/.../{cruise}_{id}_r2rnav/).
    Reads bag-info.txt for DOI, size, license, and data/ for file formats.
    """
    ncei_url = ncei_url.rstrip("/") + "/"
    result: dict = {"source_url": ncei_url, "access": "open"}

    # ── bag-info.txt ──────────────────────────────────────────────────────────
    bag_url = ncei_url + "bag-info.txt"
    try:
        r = get(bag_url)
        for line in r.text.splitlines():
            key, _, val = line.partition(":")
            val = val.strip()
            k = key.strip()
            if k == "External-Identifier":
                doi_raw = val.replace("doi:", "").strip()
                result["doi"] = doi_raw
                result["doi_url"] = f"https://doi.org/{doi_raw}"
            elif k == "Bag-Size":
                result["size_str"] = val
                result["size_gb"] = _parse_size(val)
            elif k == "Internal-Sender-Description":
                result["description"] = val
            elif k == "R2R-ProcessType":
                result["classification"] = "PROCESSED" if val == "processed" else "RAW"
            elif k == "R2R-License":
                result["license"] = val
            elif k == "Bagging-Date":
                result["date_released"] = val[:10]  # YYYY-MM-DD
    except Exception as exc:
        print(f"  WARNING: could not fetch bag-info.txt: {exc}", file=sys.stderr)

    # ── data/ subdirectory — detect file formats ──────────────────────────────
    data_url = ncei_url + "data/"
    try:
        r = get(data_url)
        # Extract filenames from Apache directory listing hrefs
        filenames = re.findall(r'href="([^"?/][^"]*)"', r.text)
        exts = sorted({f.rsplit(".", 1)[-1].upper() for f in filenames if "." in f})
        if exts:
            result["format_str"] = ", ".join(exts)
            result["_data_files"] = filenames
    except Exception as exc:
        print(f"  WARNING: could not fetch data/ directory: {exc}", file=sys.stderr)

    return result


def parse_r2r_fileset(url: str) -> dict:
    """
    Parse an R2R fileset URL. Handles three cases:
    - www.rvdata.us/search/fileset/{id}  → R2R search page
    - service.rvdata.us/...              → follows redirect (typically to NCEI BagIt dir)
    """
    print(f"  Fetching R2R fileset: {url}")
    try:
        r = get(url)
    except requests.HTTPError as exc:
        print(f"  WARNING: {exc} — skipping detail fetch", file=sys.stderr)
        return {"source_url": url, "access": "open"}

    final_url = r.url

    # Redirected to NCEI BagIt directory → use dedicated parser
    if "ncei.noaa.gov" in final_url:
        print(f"  -> Redirected to NCEI: {final_url}")
        return parse_ncei_bagit_dir(final_url)

    # Regular rvdata.us search page
    text = strip_tags(r.text)
    result: dict = {"source_url": final_url}

    # DOI
    doi_m = re.search(r"Data DOI:\s*(https?://doi\.org/[\S]+)", text)
    if doi_m:
        result["doi"] = doi_m.group(1).replace("https://doi.org/", "").rstrip(".")
        result["doi_url"] = f"https://doi.org/{result['doi']}"

    # Abstract
    abs_m = re.search(r"Abstract\s+(.+?)\s+(?:Vessel Name|Spatial Extent|Data Released)", text)
    if abs_m:
        result["description"] = html_module.unescape(abs_m.group(1).strip())

    # Format
    fmt_m = re.search(r"Format:\s+(.+?)\s+(?:File Count|Data Released|Spatial)", text)
    if fmt_m:
        result["format_str"] = fmt_m.group(1).strip()

    # File Count
    fc_m = re.search(r"File Count:\s+(\d+)", text)
    if fc_m:
        result["file_count"] = int(fc_m.group(1))

    # File Set Size
    size_m = re.search(r"File Set Size:\s+([\d.]+\s*(?:KB|MB|GB|TB))", text, re.I)
    if size_m:
        result["size_str"] = size_m.group(1).strip()
        result["size_gb"] = _parse_size(result["size_str"])

    # Spatial extent
    for label, key in [("N:", "lat_max"), ("S:", "lat_min"), ("E:", "lon_max"), ("W:", "lon_min")]:
        m = re.search(rf"{re.escape(label)}\s*([-\d.]+)", text)
        if m:
            result[key] = float(m.group(1))

    # Data released
    rel_m = re.search(r"Data Released:\s*(\d{4}-\d{2}-\d{2})", text)
    if rel_m:
        result["date_released"] = rel_m.group(1)

    result["access"] = "open" if "doi" in result else "restricted"
    return result


# ── MGDS DataSets page parser ─────────────────────────────────────────────────

def parse_mgds_datasets(url: str) -> list[dict]:
    """
    Parse marine-geo.org/tools/search/DataSets.php?data_set_uids=...
    Returns one dict per dataset found.
    """
    print(f"  Fetching MGDS datasets: {url}")
    r = get(url)
    text = strip_tags(r.text)

    datasets = []
    # Each dataset starts with a type like "Seismic:Navigation" or "Bathymetry" followed by DOI
    # Split on "Data DOI:"
    parts = text.split("Data DOI:")
    for part in parts[1:]:  # skip text before first DOI
        d: dict = {}

        doi_m = re.match(r"\s*([\S]+)", part)
        if doi_m:
            raw_doi = doi_m.group(1).rstrip(".")
            d["doi"] = raw_doi
            d["doi_url"] = f"https://doi.org/{raw_doi}" if not raw_doi.startswith("http") else raw_doi

        # Description — text after DOI until next structural marker
        desc_m = re.search(r"acquired during .+?(?=Platform Info|File Format|Bangs|Trehu|$)", part[:500])
        if desc_m:
            d["description"] = desc_m.group(0).strip()

        # Format
        fmt_m = re.search(r"File Format\s+(\S+)", part)
        if fmt_m:
            d["format_str"] = fmt_m.group(1).strip()

        datasets.append(d)

    print(f"    Found {len(datasets)} MGDS datasets")
    return datasets


# ── Top-level: enrich sensors → dataset entries ───────────────────────────────

def _fetch_sensor_detail(url: str) -> dict:
    """
    Dispatch to the appropriate detail-page parser based on URL shape.
    Returns a detail dict (may be empty if URL type is unrecognised).
    """
    if not url:
        return {}
    try:
        if "rvdata.us" in url:
            return parse_r2r_fileset(url)
        if "DataSets.php" in url:
            sub_datasets = parse_mgds_datasets(url)
            if not sub_datasets:
                return {}
            dois = [d["doi"] for d in sub_datasets if "doi" in d]
            fmts = [d["format_str"] for d in sub_datasets if "format_str" in d]
            return {
                "source_url": url,
                "sub_dois": dois,
                "format_str": ", ".join(sorted(set(fmts))),
                "description": sub_datasets[0].get("description", ""),
                "access": "open",
            }
        # Unknown URL type (IRIS, Files.php, etc.) — no detail fetch
        return {}
    except Exception as exc:
        print(f"  WARNING: failed to fetch {url}: {exc}", file=sys.stderr)
        return {}


def _build_dataset_entry(sensor: dict, detail: dict) -> dict:
    """
    Map sensor surface info + fetched detail dict into our paper JSON schema
    dataset entry.  Private keys (_*) carry extra provenance for review.
    """
    # Resolve data_type (handles combined strings like "Bathymetry:Singlebeam, Gravity:Field")
    raw_type_key = sensor["raw_type"].lower()
    data_type = DATA_TYPE_MAP.get(raw_type_key)
    if data_type is None:
        for part in re.split(r"[,;]", raw_type_key):
            data_type = DATA_TYPE_MAP.get(part.strip())
            if data_type:
                break
    data_type = data_type or "unknown"

    repo_raw = (sensor.get("repo_raw") or "").strip()
    repo = REPO_MAP.get(repo_raw.lower(), repo_raw) if repo_raw else None

    fmt_raw = sensor.get("fmt_raw") or detail.get("format_str") or ""
    formats = [f.strip() for f in re.split(r"[,/]", fmt_raw) if f.strip()] or None

    url = sensor.get("url", "")
    entry: dict = {
        "data_type":      data_type,
        "name":           sensor["raw_type"],
        "classification": detail.get("classification", "RAW"),
        "format":         formats,
        "url":            detail.get("doi_url") or url or None,
        "doi":            detail.get("doi"),
        "repository":     [repo] if repo else None,
        "size_gb":        detail.get("size_gb"),
        "access":         detail.get("access", "unknown"),
        "download_command": None,
        "description":    detail.get("description", ""),
        "cdp_spacing_m":  None,
    }

    for key in ("sub_dois", "file_count", "size_str", "date_released"):
        if detail.get(key):
            entry[f"_{key}"] = detail[key]
    if detail.get("lat_min") is not None:
        entry["_bbox"] = {
            "lat_min": detail["lat_min"], "lat_max": detail["lat_max"],
            "lon_min": detail["lon_min"], "lon_max": detail["lon_max"],
        }

    return entry


def enrich_sensor(sensor: dict) -> dict:
    """Fetch detail page for a sensor and merge into a dataset entry."""
    detail = _fetch_sensor_detail(sensor.get("url", ""))
    return _build_dataset_entry(sensor, detail)


def scrape_cruise(cruise_id: str) -> list[dict]:
    sensors = parse_mgds_entry(cruise_id)
    datasets = []
    for sensor in sensors:
        print(f"\nProcessing: {sensor['raw_type']}")
        entry = enrich_sensor(sensor)
        datasets.append(entry)
        time.sleep(0.5)  # be polite
    return datasets


# ── Patch paper JSON ──────────────────────────────────────────────────────────

def patch_paper(paper_id: str, datasets: list[dict], dry_run: bool = False) -> None:
    path = PAPERS_DIR / f"{paper_id}.json"
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        return

    paper = json.loads(path.read_text(encoding="utf-8"))
    old_data = paper.get("data", [])
    print(f"\nCurrent data entries: {len(old_data)}")
    print(f"Scraped datasets:     {len(datasets)}")

    # Strip internal _* keys before writing
    clean = [{k: v for k, v in d.items() if not k.startswith("_")} for d in datasets]

    if dry_run:
        print("\n[dry-run] Would replace paper['data'] with:")
        print(json.dumps(clean, indent=2, ensure_ascii=False))
        return

    paper["data"] = clean
    path.write_text(json.dumps(paper, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Patched {path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Scrape MGDS cruise data and enrich paper JSON")
    ap.add_argument("--cruise", required=True, help="Cruise ID, e.g. MGL1701")
    ap.add_argument("--paper", help="Paper JSON id to patch, e.g. bangs_2020_basal_accretion_jgr")
    ap.add_argument("--dry-run", action="store_true", help="Print result without writing")
    ap.add_argument("--out", help="Save scraped datasets to this JSON file")
    args = ap.parse_args()

    datasets = scrape_cruise(args.cruise)

    print("\n" + "=" * 60)
    print(f"Scraped {len(datasets)} datasets for cruise {args.cruise}")
    print("=" * 60)
    print(json.dumps(datasets, indent=2, ensure_ascii=False))

    if args.out:
        Path(args.out).write_text(json.dumps(datasets, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nSaved to {args.out}")

    if args.paper:
        patch_paper(args.paper, datasets, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
