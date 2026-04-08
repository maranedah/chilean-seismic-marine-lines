"""
pangaea.py — Scrape metadata from a PANGAEA dataset DOI.

Fetches the ?format=textfile tab file, parses the /* ... */ metadata block,
detects the Binary (Size) column, and sums total dataset size.

Usage:
    python -m src.scraper.pangaea --doi 10.1594/PANGAEA.983166
    python -m src.scraper.pangaea --doi 10.1594/PANGAEA.983166 --paper volker_2011_...
    python -m src.scraper.pangaea --cruise SO211              # search all datasets
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

PAPERS_DIR = Path(__file__).parent.parent.parent / "data" / "extracted_jsons"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

# Map PANGAEA keyword/title hints → our schema data_type
PANGAEA_TYPE_MAP = [
    (r"seismic\s+refle",          "seismic_reflection_mcs"),
    (r"seismic\s+refra|obs\b|obh\b", "seismic_refraction_obs"),
    (r"multibeam|bathymetry|swath.bath|em[- ]?\d{2,3}", "bathymetry"),
    (r"backscatter",               "backscatter"),
    (r"sub.?bottom|parasound|chirp|3\.5\s?khz", "subbottom"),
    (r"gravity|gravimeter|faa\b",  "gravity"),
    (r"magnetic|magnetometer",     "magnetics"),
    (r"navigation|gps\b|gnss\b",   "navigation"),
    (r"sound velocity|xbt\b|xctd|ctd\b", "velocity_sound"),
]


# ── HTTP ──────────────────────────────────────────────────────────────────────

def get(url: str, timeout: int = 30) -> requests.Response:
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


# ── Tab file parser ───────────────────────────────────────────────────────────

def _parse_size_str(val: str) -> Optional[float]:
    """'4.7 MBytes' → bytes as float. Returns None if unparseable."""
    m = re.match(r"([\d.]+)\s*(K|M|G|T)?Bytes", val.strip(), re.I)
    if not m:
        return None
    num = float(m.group(1))
    unit = (m.group(2) or "").upper()
    if unit == "K": return num * 1024
    if unit == "M": return num * 1024 ** 2
    if unit == "G": return num * 1024 ** 3
    if unit == "T": return num * 1024 ** 4
    return num


def _resolve_data_type(text: str) -> str:
    """Guess our data_type from a free-text description/keyword string."""
    low = text.lower()
    for pattern, dtype in PANGAEA_TYPE_MAP:
        if re.search(pattern, low):
            return dtype
    return "unknown"


def _detect_formats(data_lines: list[str], binary_col: int) -> list[str]:
    """Collect unique file extensions from the Binary Object filename column (col 1)."""
    exts: set[str] = set()
    for line in data_lines[:200]:  # sample first 200 rows
        parts = line.split("\t")
        if len(parts) > 1:
            fname = parts[1].strip()
            if "." in fname:
                ext = fname.rsplit(".", 1)[-1].upper()
                if 2 <= len(ext) <= 6 and ext.isalpha():
                    exts.add(ext)
    return sorted(exts) or None


def _split_tab_lines(lines: list[str]) -> tuple[list[str], Optional[str], list[str]]:
    """Split raw tab-file lines into (meta_lines, header_line, data_lines)."""
    meta_lines: list[str] = []
    header_line: Optional[str] = None
    data_lines: list[str] = []
    in_meta = True

    for line in lines:
        if in_meta:
            if line.strip() == "*/":
                in_meta = False
            else:
                meta_lines.append(line)
        elif header_line is None:
            if line.strip():
                header_line = line  # first non-empty line after */ is the column header
        else:
            if line.strip():
                data_lines.append(line)

    return meta_lines, header_line, data_lines


def _parse_meta_block(meta_lines: list[str]) -> dict[str, str]:
    """Parse the /* ... */ metadata block into a key→value dict."""
    meta: dict[str, str] = {}
    current_key = None
    for line in meta_lines:
        m = re.match(r"^([A-Za-z][^:]*?):\t(.*)", line)
        if m:
            current_key = m.group(1).strip()
            meta[current_key] = m.group(2).strip()
        elif current_key and line.startswith("\t"):
            meta[current_key] = meta[current_key] + " " + line.strip()
    return meta


def parse_pangaea_tab(doi: str) -> dict:
    """
    Fetch the ?format=textfile for a PANGAEA DOI and return a dataset metadata dict.
    DOI may be bare (10.1594/PANGAEA.983166) or a full URL.
    """
    doi = re.sub(r"^https?://doi\.(?:org|pangaea\.de)/", "", doi).strip().rstrip("/")
    tab_url = f"https://doi.pangaea.de/{doi}?format=textfile"
    page_url = f"https://doi.org/{doi}"

    print(f"  Fetching PANGAEA tab: {tab_url}")
    r = get(tab_url, timeout=60)
    meta_lines, header_line, data_lines = _split_tab_lines(r.text.splitlines())
    meta = _parse_meta_block(meta_lines)

    result: dict = {"doi": doi, "doi_url": page_url, "repository": ["PANGAEA"]}

    # Citation → title
    cit = meta.get("Citation", "")
    # Title is the part after the year and before [dataset]
    title_m = re.search(r"\(\d{4}\):\s+(.+?)(?:\s+\[dataset\]|\.\s+PANGAEA)", cit)
    if title_m:
        result["title"] = title_m.group(1).strip()

    # Abstract
    result["description"] = meta.get("Abstract", "").strip()

    # Keywords → data_type
    keywords = meta.get("Keyword(s)", "") or meta.get("Keywords", "")
    result["keywords"] = [k.strip() for k in keywords.split(";") if k.strip()]
    hint_text = keywords + " " + result.get("title", "")
    result["data_type"] = _resolve_data_type(hint_text)

    # Coverage → bbox, dates
    cov = meta.get("Coverage", "")
    for label, key in [
        ("SOUTH-BOUND LATITUDE", "lat_min"), ("NORTH-BOUND LATITUDE", "lat_max"),
        ("WEST-BOUND LONGITUDE",  "lon_min"), ("EAST-BOUND LONGITUDE",  "lon_max"),
    ]:
        m = re.search(rf"{label}:\s*([-\d.]+)", cov, re.I)
        if m:
            result[key] = float(m.group(1))

    for label, key in [("DATE/TIME START", "date_start"), ("DATE/TIME END", "date_end")]:
        m = re.search(rf"{label}:\s*(\S+)", cov, re.I)
        if m:
            result[key] = m.group(1)

    # Campaign from Event
    event = meta.get("Event(s)", "")
    camp_m = re.search(r"CAMPAIGN:\s*([^\s(*]+)", event)
    if camp_m:
        result["campaign"] = camp_m.group(1).strip()
    vessel_m = re.search(r"BASIS:\s*([^(]+?)(?:\s*\(|$)", event)
    if vessel_m:
        result["vessel"] = vessel_m.group(1).strip()

    # License → access
    lic = meta.get("License", "")
    if "creative commons" in lic.lower() or "cc-by" in lic.lower() or "public domain" in lic.lower():
        result["access"] = "open"
    elif "restricted" in lic.lower() or "proprietary" in lic.lower():
        result["access"] = "restricted"
    else:
        result["access"] = "open"  # PANGAEA default is open after publication

    # Classification (processing level)
    proc_m = re.search(r"ProcLevel(\d)", meta.get("Status", "") + " ".join(meta_lines[-5:]))
    if proc_m:
        level = int(proc_m.group(1))
        # PANGAEA levels: 0=raw, 1=basic QC, 2=processed, 3=interpreted
        result["classification"] = "RAW" if level <= 1 else "PROCESSED"
    else:
        result["classification"] = "RAW"

    # ── Parse column header → find Binary (Size) column ──────────────────────
    size_gb: Optional[float] = None
    formats: Optional[list[str]] = None

    if header_line:
        col_headers = header_line.split("\t")
        size_col_idx = next(
            (j for j, h in enumerate(col_headers) if "Binary (Size)" in h or ("Size" in h and "Bytes" in h)),
            None
        )
        has_binary = any("Binary" in h for h in col_headers)

        if size_col_idx is not None and data_lines:
            total_bytes = 0.0
            n = 0
            for dline in data_lines:
                parts = dline.split("\t")
                if len(parts) > size_col_idx:
                    b = _parse_size_str(parts[size_col_idx])
                    if b is not None:
                        total_bytes += b
                        n += 1
            if n:
                size_gb = round(total_bytes / 1024 ** 3, 3)
                result["_file_count"] = n
                result["_size_str"] = f"{total_bytes/1024**2:.1f} MB" if total_bytes < 1e9 else f"{size_gb:.2f} GB"

        if has_binary and data_lines:
            formats = _detect_formats(data_lines, size_col_idx or 1)

    result["size_gb"] = size_gb
    result["format"] = formats

    return result


# ── PANGAEA search API ────────────────────────────────────────────────────────

def search_pangaea_cruise(cruise_id: str, limit: int = 200) -> list[dict]:
    """
    Search PANGAEA for all datasets from a given cruise/campaign ID.
    Returns list of {doi, title, data_type_hint} dicts.
    """
    # Use the simpler public API
    api_url = f"https://www.pangaea.de/api/finddata?term={cruise_id}&count={limit}&offset=0&format=json"
    print(f"Searching PANGAEA: {api_url}")
    try:
        r = get(api_url, timeout=20)
        data = r.json()
        hits = data.get("results", [])
        results = []
        for h in hits:
            doi = h.get("URI", "").replace("https://doi.org/", "").replace("https://doi.pangaea.de/", "")
            title = h.get("citation", {}).get("title", "")
            results.append({"doi": doi, "title": title})
        print(f"  Found {len(results)} PANGAEA datasets for {cruise_id}")
        return results
    except Exception as exc:
        print(f"  WARNING: PANGAEA search failed: {exc}", file=sys.stderr)
        return []


# ── Build dataset entry ───────────────────────────────────────────────────────

def to_dataset_entry(meta: dict) -> dict:
    """Convert parse_pangaea_tab result to our paper JSON schema dataset entry."""
    entry = {
        "data_type":      meta.get("data_type", "unknown"),
        "name":           meta.get("title", meta["doi"]),
        "classification": meta.get("classification", "RAW"),
        "format":         meta.get("format"),
        "url":            meta["doi_url"],
        "doi":            meta["doi"],
        "repository":     meta["repository"],
        "size_gb":        meta.get("size_gb"),
        "access":         meta.get("access", "open"),
        "download_command": None,
        "description":    meta.get("description", ""),
        "cdp_spacing_m":  None,
    }
    # Carry extra info with _ prefix
    for k in ("_file_count", "_size_str", "date_start", "date_end", "campaign", "vessel", "keywords"):
        if k in meta:
            entry[f"_{k.lstrip('_')}"] = meta[k]
    return entry


# ── Patch paper JSON ──────────────────────────────────────────────────────────

def patch_paper(paper_id: str, new_entry: dict, dry_run: bool = False) -> None:
    path = PAPERS_DIR / f"{paper_id}.json"
    if not path.exists():
        print(f"  ERROR: {path} not found", file=sys.stderr)
        return

    paper = json.loads(path.read_text(encoding="utf-8"))
    existing = paper.get("data") or []

    # Check dedup
    for d in existing:
        if d.get("doi") == new_entry["doi"]:
            print(f"  {paper_id}: DOI {new_entry['doi']} already present — skipping")
            return

    clean = {k: v for k, v in new_entry.items() if not k.startswith("_")}
    print(f"  {paper_id}: adding {clean['data_type']} dataset (doi={clean['doi']})")

    if dry_run:
        print(f"    [dry-run] {json.dumps(clean, ensure_ascii=False)[:200]}")
        return

    paper["data"] = existing + [clean]
    path.write_text(json.dumps(paper, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Scrape a PANGAEA dataset or search by cruise")
    ap.add_argument("--doi",    help="PANGAEA DOI, e.g. 10.1594/PANGAEA.983166")
    ap.add_argument("--cruise", help="Cruise ID to search on PANGAEA, e.g. SO211")
    ap.add_argument("--paper",  help="Paper ID to patch with scraped dataset")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out",    help="Save result JSON to file")
    args = ap.parse_args()

    if not args.doi and not args.cruise:
        ap.error("Provide --doi or --cruise")

    dois_to_scrape: list[str] = []

    if args.doi:
        dois_to_scrape.append(args.doi)

    if args.cruise:
        hits = search_pangaea_cruise(args.cruise)
        dois_to_scrape.extend(h["doi"] for h in hits if h.get("doi"))

    results = []
    for doi in dois_to_scrape:
        try:
            meta = parse_pangaea_tab(doi)
            entry = to_dataset_entry(meta)
            results.append(entry)
            print(f"  data_type={entry['data_type']}  size={meta.get('_size_str','?')}  "
                  f"files={meta.get('_file_count','?')}  access={entry['access']}")
            if args.paper:
                patch_paper(args.paper, entry, dry_run=args.dry_run)
            time.sleep(0.5)
        except Exception as exc:
            print(f"  ERROR scraping {doi}: {exc}", file=sys.stderr)

    print("\n" + "=" * 60)
    print(json.dumps(results, indent=2, ensure_ascii=False))

    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
