"""
download.py — Chilean Marine Seismic Lines data downloader

Downloads datasets referenced in the paper JSON files.

Usage:
    python download.py --all
    python download.py --paper warwel_2025_copiapo_refraction
    python download.py --classification RAW
    python download.py --access open
    python download.py --region "North Chile"
    python download.py --all --output ./data/ --dry-run
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

PAPERS_DIR = Path(__file__).parent / "papers"
DATA_DIR = Path(__file__).parent / "data"


def load_papers(papers_dir: Path) -> list[dict]:
    """Load all individual paper JSONs (excludes survey_results and data_availability)."""
    exclude = {"survey_results.json", "data_availability.json", "schema.json"}
    papers = []
    for f in sorted(papers_dir.glob("*.json")):
        if f.name in exclude:
            continue
        with open(f, encoding="utf-8") as fh:
            papers.append(json.load(fh))
    return papers


def get_region(paper: dict) -> str:
    lat = paper.get("location", {}).get("latitude")
    if lat is None:
        return "Unknown"
    if lat >= -30:
        return "North Chile"
    if lat >= -40:
        return "Central Chile"
    return "South Chile"


def filter_papers(
    papers: list[dict],
    paper_id: str | None = None,
    classification: str | None = None,
    access: str | None = None,
    region: str | None = None,
) -> list[dict]:
    result = []
    for paper in papers:
        if paper_id and paper["id"] != paper_id:
            continue
        datasets = paper.get("data", [])
        if classification:
            datasets = [d for d in datasets if d.get("classification") == classification.upper()]
        if access:
            datasets = [d for d in datasets if d.get("access") == access.lower()]
        if region:
            if get_region(paper).lower() != region.lower():
                continue
        if datasets:
            result.append({**paper, "data": datasets})
    return result


def download_dataset(dataset: dict, paper_id: str, output_dir: Path, dry_run: bool = False) -> bool:
    url = dataset.get("url")
    if not url:
        print(f"  [SKIP] No URL available for: {dataset.get('name', 'unnamed dataset')}")
        return False

    name = dataset.get("name", "dataset").replace(" ", "_").replace("/", "-")[:60]
    fmt = dataset.get("format", "dat").lower().split("/")[0]
    filename = f"{paper_id}_{name}.{fmt}"
    dest = output_dir / paper_id / filename
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        print(f"  [EXISTS] {dest.relative_to(output_dir.parent)}")
        return True

    print(f"  [{'DRY-RUN' if dry_run else 'DOWNLOAD'}] {dataset.get('name')}")
    print(f"    URL : {url}")
    print(f"    Dest: {dest.relative_to(output_dir.parent)}")

    if dry_run:
        return True

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk = 65536
            with open(dest, "wb") as f:
                while True:
                    block = response.read(chunk)
                    if not block:
                        break
                    f.write(block)
                    downloaded += len(block)
                    if total:
                        pct = downloaded / total * 100
                        print(f"\r    {downloaded/1e6:.1f} MB / {total/1e6:.1f} MB ({pct:.0f}%)", end="")
            print()
        print(f"  [OK] Saved to {dest.relative_to(output_dir.parent)}")
        return True
    except urllib.error.HTTPError as e:
        print(f"  [ERROR] HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        print(f"  [ERROR] {e.reason}")
    except Exception as e:
        print(f"  [ERROR] {e}")
    return False


def print_availability_report(papers: list[dict]) -> None:
    # use the already-loaded list — avoids re-reading all 98 JSONs from disk
    total = len(papers)
    open_count = sum(
        1 for p in papers if any(d.get("access") == "open" for d in p.get("data", []))
    )
    restricted = sum(
        1 for p in papers if any(d.get("access") == "restricted" for d in p.get("data", []))
    )
    unknown = total - open_count - restricted

    cls_counts = {"RAW": 0, "SEMI_PROCESSED": 0, "PROCESSED": 0}
    for p in papers:
        for d in p.get("data", []):
            c = d.get("classification", "PROCESSED")
            cls_counts[c] = cls_counts.get(c, 0) + 1

    print("\n=== Data Availability Report ===")
    print(f"  Total papers      : {total}")
    print(f"  Open-access data  : {open_count}")
    print(f"  Restricted data   : {restricted}")
    print(f"  Unknown access    : {unknown}")
    print(f"  Classification    : {cls_counts}")

    print("\n--- Papers with open data ---")
    for p in papers:
        open_ds = [d for d in p.get("data", []) if d.get("url") and d.get("access") == "open"]
        if open_ds:
            print(f"  [{p['year']}] {p['title'][:70]}")
            for d in open_ds:
                print(f"       {d['classification']} | {d['url']}")

    print("\n--- Papers with no accessible data ---")
    for p in papers:
        no_url = all(not d.get("url") for d in p.get("data", []))
        if no_url:
            print(f"  [{p['year']}] {p['id']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Chilean marine seismic datasets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Download all available (open-access) datasets")
    group.add_argument("--paper", metavar="ID", help="Download datasets for a specific paper by ID")
    group.add_argument("--report", action="store_true", help="Show data availability report without downloading")

    parser.add_argument(
        "--classification",
        choices=["RAW", "SEMI_PROCESSED", "PROCESSED"],
        help="Filter by data classification",
    )
    parser.add_argument(
        "--access",
        choices=["open", "restricted", "unknown"],
        default="open",
        help="Filter by access type (default: open)",
    )
    parser.add_argument(
        "--region",
        choices=["North Chile", "Central Chile", "South Chile"],
        help="Filter by geographic region",
    )
    parser.add_argument(
        "--output",
        metavar="DIR",
        default=str(DATA_DIR),
        help=f"Output directory (default: {DATA_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        metavar="SECONDS",
        help="Delay between downloads in seconds (default: 1.0)",
    )

    args = parser.parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.report:
        all_papers = load_papers(PAPERS_DIR)
        print_availability_report(all_papers)
        return

    all_papers = load_papers(PAPERS_DIR)

    if args.all:
        papers = filter_papers(
            all_papers,
            classification=args.classification,
            access=args.access,
            region=args.region,
        )
    else:
        papers = filter_papers(all_papers, paper_id=args.paper, access=None)

    if not papers:
        print("No papers matched the given filters.")
        sys.exit(0)

    total_datasets = sum(len(p["data"]) for p in papers)
    print(f"Found {len(papers)} paper(s) with {total_datasets} dataset(s) to process.\n")

    success = 0
    skipped = 0
    failed = 0

    for paper in papers:
        print(f"[{paper['year']}] {paper['title'][:80]}")
        print(f"  ID: {paper['id']} | {get_region(paper)} | {paper.get('location', {}).get('city', 'Unknown')}")
        for dataset in paper.get("data", []):
            result = download_dataset(dataset, paper["id"], output_dir, dry_run=args.dry_run)
            if result:
                if dataset.get("url"):
                    success += 1
                else:
                    skipped += 1
            else:
                if dataset.get("url"):
                    failed += 1
                else:
                    skipped += 1
            if dataset.get("url") and not args.dry_run:
                time.sleep(args.delay)
        print()

    print("=== Download Summary ===")
    print(f"  Downloaded : {success}")
    print(f"  Skipped    : {skipped} (no URL or already exists)")
    print(f"  Failed     : {failed}")


if __name__ == "__main__":
    main()
