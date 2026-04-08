"""
Queries the PANGAEA REST API to fill in size_gb for dataset entries
whose DOI resolves to a PANGAEA record (doi.pangaea.de or 10.1594/PANGAEA.*).

Usage:
    python -m src.enrich.pangaea [--dry-run]

The script:
  1. Scans papers/ for data entries with a PANGAEA DOI (not yet replaced by dataset_ref)
  2. Also scans datasets/ for dataset files with a PANGAEA DOI
  3. Queries https://ws.pangaea.de/oai/provider?verb=GetRecord&metadataPrefix=oai_dc&identifier=oai:pangaea.de:doi:<DOI>
     to get file size metadata.
  4. Updates size_gb in-place if a size is found and the current value is null.

PANGAEA API notes:
  - REST endpoint: GET https://api.pangaea.de/datasets/{doi_suffix}
    Returns JSON with a "fileSize" field (in bytes) when available.
  - Example: https://api.pangaea.de/datasets/10.1594/PANGAEA.893033
  - The DOI suffix is everything after "10.1594/" — but also works with full DOI.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# Fix Windows console encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent.parent

PANGAEA_DOI_PAGE = "https://doi.pangaea.de/{doi}"

def is_pangaea_doi(doi):
    return doi and ("PANGAEA" in doi.upper() or "pangaea" in doi.lower())

def extract_pangaea_doi(doi, url):
    """Return the canonical PANGAEA DOI string, or None."""
    if doi and is_pangaea_doi(doi):
        return doi
    if url and "pangaea.de" in url:
        m = re.search(r"10\.\d{4}/PANGAEA\.\d+", url)
        if m:
            return m.group(0)
    return None

def fetch_pangaea_size(doi, verbose=True):
    """
    Returns size in GB by scraping the PANGAEA DOI landing page.
    Looks for:
      <meta name="DC.format" content="application/octet-stream, 42.3 MBytes" />
    doi: full DOI string, e.g. "10.1594/PANGAEA.893033"
    """
    url = PANGAEA_DOI_PAGE.format(doi=doi)
    if verbose:
        print(f"  GET {url}")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; chilean-seismic-db/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read(16384).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"    HTTP {e.code} - skipping")
        return None
    except Exception as e:
        print(f"    Error: {e} - skipping")
        return None

    # Primary: <meta name="DC.format" content="..., 42.3 MBytes" />
    m = re.search(
        r'<meta[^>]+name=["\']DC\.format["\'][^>]+content=["\'][^"\']*?([\d,.]+)\s*(TBytes|GBytes|MBytes|KBytes|Bytes)["\']',
        html, re.IGNORECASE
    )
    if m:
        val = float(m.group(1).replace(",", ""))
        unit = m.group(2).lower()
        multipliers = {"bytes": 1e-9, "kbytes": 1e-6, "mbytes": 1e-3, "gbytes": 1.0, "tbytes": 1e3}
        return round(val * multipliers[unit], 4)

    # Fallback: any visible size string in the page text
    text = re.sub(r"<[^>]+>", " ", html)
    m = re.search(r"(\d[\d,.]*\d|\d)\s*(TB|GB|MB|KB)\s*(?:ytes)?", text, re.IGNORECASE)
    if m:
        val = float(m.group(1).replace(",", ""))
        unit = m.group(2).upper()
        multipliers = {"KB": 1e-6, "MB": 1e-3, "GB": 1.0, "TB": 1e3}
        return round(val * multipliers[unit], 4)

    if verbose:
        print(f"    No size pattern found in page")
    return None

def process_files(file_list, label, dry_run):
    updated = 0
    already_filled = 0
    no_pangaea = 0
    no_size = 0

    for fpath in sorted(file_list):
        fname = os.path.basename(fpath)
        try:
            with open(fpath, encoding="utf-8", errors="replace") as f:
                obj = json.load(f)
        except Exception as e:
            print(f"[SKIP] {fname}: {e}")
            continue

        # Handle both full paper JSONs (have "data" array) and dataset JSONs
        entries = obj.get("data") if "data" in obj else [obj]
        changed = False

        for entry in entries:
            if entry.get("size_gb") is not None:
                already_filled += 1
                continue

            doi = entry.get("doi")
            url = entry.get("url")
            pangaea_doi = extract_pangaea_doi(doi, url)
            if not pangaea_doi:
                no_pangaea += 1
                continue

            print(f"[{fname}] DOI={pangaea_doi}, size_gb=null -> querying PANGAEA...")
            size_gb = fetch_pangaea_size(pangaea_doi)
            time.sleep(0.5)  # be polite to the API

            if size_gb is not None:
                print(f"    -> {size_gb} GB")
                if not dry_run:
                    entry["size_gb"] = size_gb
                    changed = True
                updated += 1
            else:
                print(f"    -> size not available")
                no_size += 1

        if changed and not dry_run:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(obj, f, indent=2, ensure_ascii=False)
            print(f"  [SAVED] {fname}")

    print(f"\n=== {label} ===")
    print(f"  Updated:       {updated}")
    print(f"  Already filled:{already_filled}")
    print(f"  No PANGAEA DOI:{no_pangaea}")
    print(f"  Size missing:  {no_size}")
    return updated

def main():
    parser = argparse.ArgumentParser(description="Enrich size_gb from PANGAEA API")
    parser.add_argument("--dry-run", action="store_true", help="Print what would change without writing")
    parser.add_argument("--datasets-only", action="store_true", help="Only process datasets/ files")
    parser.add_argument("--papers-only", action="store_true", help="Only process papers/ files")
    args = parser.parse_args()

    if args.dry_run:
        print("[DRY RUN — no files will be modified]\n")

    total = 0

    if not args.papers_only:
        dataset_files = [str(p) for p in sorted((ROOT / "datasets").glob("*.json"))]
        print(f"=== Processing {len(dataset_files)} dataset files ===\n")
        total += process_files(dataset_files, "datasets/", args.dry_run)

    if not args.datasets_only:
        paper_files = [
            f for f in [str(p) for p in sorted((ROOT / "papers").glob("*.json"))]
            if os.path.basename(f) != "survey_results.json"
        ]
        print(f"\n=== Processing {len(paper_files)} paper files ===\n")
        total += process_files(paper_files, "papers/", args.dry_run)

    print(f"\n=== TOTAL UPDATED: {total} ===")

if __name__ == "__main__":
    main()
