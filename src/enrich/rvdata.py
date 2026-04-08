"""
Fetches file sizes for RVData fileset entries by calling the RVData JSON API.

Usage:
    python -m src.enrich.rvdata [--dry-run]

How RVData works:
  - Fileset download URLs: https://service.rvdata.us/data/cruise/CRUISEID/fileset/FILESETID
  - The RVData API exposes fileset metadata at:
      GET https://service.rvdata.us/api/fileset/FILESETID
    which returns JSON including a "total_size" field (in bytes).
  - Cruise-level browse URLs (rvdata.us/search/cruise/...) don't have a
    machine-readable size, so we skip those.

The script processes both datasets/ files and inline paper data entries.
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

FILESET_URL_RE = re.compile(
    r"service\.rvdata\.us/data/cruise/[^/]+/fileset/(\d+)"
)
# file_manifest endpoint returns per-file size_bytes for a given fileset
RVDATA_MANIFEST_API = "https://service.rvdata.us/api/file_manifest/?fileset_id={fileset_id}"

def extract_fileset_id(url):
    """Return the fileset ID integer from an RVData URL, or None."""
    if not url:
        return None
    m = FILESET_URL_RE.search(url)
    return m.group(1) if m else None

def fetch_rvdata_size(fileset_id, verbose=True):
    """
    Query the RVData file_manifest API and sum size_bytes across all files.
    Returns total size in GB, or None if unavailable / 0 files.
    """
    api_url = RVDATA_MANIFEST_API.format(fileset_id=fileset_id)
    if verbose:
        print(f"  GET {api_url}")
    try:
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "chilean-seismic-db/1.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"    HTTP {e.code} - skipping")
        return None
    except Exception as e:
        print(f"    Error: {e} - skipping")
        return None

    files = data.get("data") or []
    if not isinstance(files, list) or len(files) == 0:
        if verbose:
            print(f"    No files in manifest (fileset may use R2R/processed delivery)")
        return None

    total_bytes = sum(float(f.get("size_bytes", 0)) for f in files)
    if total_bytes == 0:
        return None

    size_gb = round(total_bytes / 1e9, 4)
    if verbose:
        print(f"    {len(files)} files summed -> {size_gb} GB")
    return size_gb

def process_files(file_list, label, dry_run):
    updated = 0
    already_filled = 0
    no_fileset = 0
    no_size = 0

    for fpath in sorted(file_list):
        fname = os.path.basename(fpath)
        try:
            with open(fpath, encoding="utf-8", errors="replace") as f:
                obj = json.load(f)
        except Exception as e:
            print(f"[SKIP] {fname}: {e}")
            continue

        entries = obj.get("data") if "data" in obj else [obj]
        changed = False

        for entry in entries:
            if "dataset_ref" in entry:
                continue
            if entry.get("size_gb") is not None:
                already_filled += 1
                continue

            url = entry.get("url") or ""
            fileset_id = extract_fileset_id(url)
            if not fileset_id:
                no_fileset += 1
                continue

            name = entry.get("name") or entry.get("id") or fname
            print(f"[{fname}] {name[:60]} → querying RVData fileset {fileset_id}...")
            size_gb = fetch_rvdata_size(fileset_id)
            time.sleep(0.5)

            if size_gb is not None:
                print(f"    → {size_gb} GB")
                if not dry_run:
                    entry["size_gb"] = size_gb
                    changed = True
                updated += 1
            else:
                print(f"    → size not found")
                no_size += 1

        if changed and not dry_run:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(obj, f, indent=2, ensure_ascii=False)
            print(f"  [SAVED] {fname}")

    print(f"\n=== {label} ===")
    print(f"  Updated:        {updated}")
    print(f"  Already filled: {already_filled}")
    print(f"  No fileset URL: {no_fileset}")
    print(f"  Size not found: {no_size}")
    return updated

def main():
    parser = argparse.ArgumentParser(description="Enrich size_gb via RVData fileset API")
    parser.add_argument("--dry-run", action="store_true", help="Print what would change without writing")
    parser.add_argument("--datasets-only", action="store_true", help="Only process datasets/ files")
    parser.add_argument("--papers-only", action="store_true", help="Only process papers/ files")
    parser.add_argument("--fileset", type=str, help="Test a single fileset ID (prints size and exits)")
    args = parser.parse_args()

    if args.fileset:
        size = fetch_rvdata_size(args.fileset)
        print(f"Fileset {args.fileset} → {size} GB")
        return

    if args.dry_run:
        print("[DRY RUN — no files will be modified]\n")

    total = 0

    if not args.papers_only:
        dataset_files = [str(p) for p in sorted((ROOT / "data" / "datasets").glob("*.json"))]
        print(f"=== Processing {len(dataset_files)} dataset files ===\n")
        total += process_files(dataset_files, "data/datasets/", args.dry_run)

    if not args.datasets_only:
        paper_files = [
            f for f in [str(p) for p in sorted((ROOT / "data" / "extracted_jsons").glob("*.json"))]
            if os.path.basename(f) != "survey_results.json"
        ]
        print(f"\n=== Processing {len(paper_files)} paper files ===\n")
        total += process_files(paper_files, "data/extracted_jsons/", args.dry_run)

    print(f"\n=== TOTAL UPDATED: {total} ===")

if __name__ == "__main__":
    main()
