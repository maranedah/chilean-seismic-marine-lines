"""
Scrapes the MGDS Files.php page for each dataset entry whose URL points to
marine-geo.org, extracting the total file size listed on that page.

Usage:
    python -m src.enrich.mgds [--dry-run]

How MGDS works:
  - Dataset listing pages: http://www.marine-geo.org/tools/search/Files.php?data_set_uid=NNNNN
  - The page lists individual files with sizes and a "Total: X.XX GB / X files" summary line.
  - We parse that summary line with a regex.

The script processes both datasets/ files and inline paper data entries (those
not yet migrated to dataset_ref, or those in datasets/).
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from html.parser import HTMLParser
from pathlib import Path

# Fix Windows console encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent.parent

MGDS_PATTERN = re.compile(
    r"marine-geo\.org/tools/search/Files\.php\?data_set_uid=(\d+)"
)

# Regexes to match a total-size line in the MGDS HTML, e.g.:
#   "Total size: 3.24 GB (1,234 files)"
#   "Total: 3.24 GB"
#   "3.24 GB | 1234 files"
SIZE_REGEXES = [
    re.compile(r"[Tt]otal\s+(?:size\s*:\s*)?([\d,.]+)\s*(TB|GB|MB|KB)", re.IGNORECASE),
    re.compile(r"([\d,.]+)\s*(TB|GB|MB|KB)\s*[|/]\s*[\d,]+\s*files", re.IGNORECASE),
    re.compile(r"([\d,.]+)\s*(TB|GB|MB|KB)\s*\([\d,]+\s*files?\)", re.IGNORECASE),
]

def parse_size_to_gb(value_str, unit):
    val = float(value_str.replace(",", ""))
    unit = unit.upper()
    multipliers = {"KB": 1e-6, "MB": 1e-3, "GB": 1.0, "TB": 1e3}
    return round(val * multipliers.get(unit, 1.0), 4)

def fetch_mgds_size(url, verbose=True):
    """Fetch an MGDS Files.php page and extract the total size. Returns GB or None."""
    # Normalise to http (MGDS redirects https → http anyway)
    fetch_url = url.replace("https://www.marine-geo.org", "http://www.marine-geo.org")
    if verbose:
        print(f"  GET {fetch_url}")
    try:
        req = urllib.request.Request(
            fetch_url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; chilean-seismic-db/1.0)",
                "Accept": "text/html",
            }
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"    HTTP {e.code} — skipping")
        return None
    except Exception as e:
        print(f"    Error: {e} — skipping")
        return None

    # Try each regex against the full page text (strip tags first for cleaner matching)
    # Quick tag-strip using regex (good enough for size-line extraction)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)

    for pattern in SIZE_REGEXES:
        m = pattern.search(text)
        if m:
            size_gb = parse_size_to_gb(m.group(1), m.group(2))
            return size_gb

    if verbose:
        # Print a snippet around "Total" for debugging
        idx = text.lower().find("total")
        snippet = text[max(0, idx-20):idx+80] if idx >= 0 else "(no 'total' found)"
        print(f"    No size pattern matched. Snippet: {snippet!r}")
    return None

def is_mgds_url(url):
    return url and bool(MGDS_PATTERN.search(url))

def process_files(file_list, label, dry_run):
    updated = 0
    already_filled = 0
    no_mgds = 0
    no_size = 0

    for fpath in sorted(file_list):
        fname = os.path.basename(fpath)
        try:
            with open(fpath, encoding="utf-8", errors="replace") as f:
                obj = json.load(f)
        except Exception as e:
            print(f"[SKIP] {fname}: {e}")
            continue

        # Handle both paper JSONs (have "data" array) and standalone dataset files
        entries = obj.get("data") if "data" in obj else [obj]
        changed = False

        for entry in entries:
            # Skip refs (they have dataset_ref, no url field)
            if "dataset_ref" in entry:
                continue
            if entry.get("size_gb") is not None:
                already_filled += 1
                continue

            url = entry.get("url") or ""
            # Also check url_alt for MGL1701 MCS dataset file
            url_alt = entry.get("url_alt") or ""

            mgds_url = None
            if is_mgds_url(url):
                mgds_url = url
            elif is_mgds_url(url_alt):
                mgds_url = url_alt

            if not mgds_url:
                no_mgds += 1
                continue

            name = entry.get("name") or entry.get("id") or fname
            print(f"[{fname}] {name[:60]} → scraping MGDS...")
            size_gb = fetch_mgds_size(mgds_url)
            time.sleep(1.0)  # polite crawl rate

            if size_gb is not None:
                print(f"    -> {size_gb} GB")
                if not dry_run:
                    entry["size_gb"] = size_gb
                    changed = True
                updated += 1
            else:
                print(f"    -> size not found")
                no_size += 1

        if changed and not dry_run:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(obj, f, indent=2, ensure_ascii=False)
            print(f"  [SAVED] {fname}")

    print(f"\n=== {label} ===")
    print(f"  Updated:        {updated}")
    print(f"  Already filled: {already_filled}")
    print(f"  No MGDS URL:    {no_mgds}")
    print(f"  Size not found: {no_size}")
    return updated

def main():
    parser = argparse.ArgumentParser(description="Enrich size_gb by scraping MGDS Files.php pages")
    parser.add_argument("--dry-run", action="store_true", help="Print what would change without writing")
    parser.add_argument("--datasets-only", action="store_true", help="Only process datasets/ files")
    parser.add_argument("--papers-only", action="store_true", help="Only process papers/ files")
    parser.add_argument("--uid", type=str, help="Test a single MGDS data_set_uid (prints size and exits)")
    args = parser.parse_args()

    if args.uid:
        test_url = f"http://www.marine-geo.org/tools/search/Files.php?data_set_uid={args.uid}"
        size = fetch_mgds_size(test_url)
        print(f"UID {args.uid} → {size} GB")
        return

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
