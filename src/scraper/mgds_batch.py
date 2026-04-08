"""
mgds_batch.py — Batch scrape all MGDS cruises and patch paper JSONs.

Discovered cruises with MGDS data: AT26-09, MGL1610, MGL1701, RC2901, RC2902

Papers with multiple cruises get datasets merged (cruise name added to description).

Usage:
    python -m src.scraper.mgds_batch --dry-run       # preview, no writes
    python -m src.scraper.mgds_batch                  # patch all paper JSONs
    python -m src.scraper.mgds_batch --cruise MGL1610 # only one cruise
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .mgds import scrape_cruise

PAPERS_DIR = Path(__file__).parent.parent.parent / "data" / "extracted_jsons"

# ── Cruise → paper mapping (from probe_cruises.py results) ───────────────────

CRUISE_PAPERS: dict[str, list[str]] = {
    "AT26-09": [
        "trehu_2019_geologic_controls_geosphere",
        "trehu_2020_postseismic_prism_geosphere",
    ],
    "MGL1610": [
        "geersen_2018_north_chile_active_tectonics",
        "gonzalez_2023_northern_forearc_mcs",
        "ma_2022_megathrust_reflectivity_iquique_natcomm",
        "ma_2023_iquique_ridge_impact",
        "myers_2022_iquique_ridge_crustal",
        "reginato_2020_iquique_wedge_tecto",
        "trehu_2023_imaging_megathrust_summary",
    ],
    "MGL1701": [
        "arnulf_2022_images_underplating_chile_jgr",
        "bangs_2020_basal_accretion_jgr",
        "maksymowicz_2021_deep_structure_south_central_jgr",
        "olsen_2020_thick_sediment_epsl",
        "trehu_2023_imaging_megathrust_summary",
    ],
    "RC2901": [
        "geersen_2011_south_chile_forearc_tectonics",
        "maksymowicz_2012_chile_triple_junction",
        "ranero_von_huene_2000_tectonic_processes_springer",
        "scherwath_2009_deep_south_central_gji",
        "tinivella_2021_gas_hydrate_system_chile_energies",
        "vargas-cordero_2010_bsr_arauco_coyhaique_springer",
        "vargas-cordero_2017_itata_valdivia_gas_hydrate_energies",
        "vargas-cordero_2018_mocha_island_seeps_energies",
        "vargas-cordero_2019_chile_triple_junction_hydrate_mdpi",
        "volker_2011_thermal_control_seismogenic_jgr",
    ],
    "RC2902": [
        "ranero_von_huene_2000_tectonic_processes_springer",
        "tinivella_2021_gas_hydrate_system_chile_energies",
    ],
}


# ── Dataset merging ───────────────────────────────────────────────────────────

def _tag_cruise(datasets: list[dict], cruise_id: str) -> list[dict]:
    """Add cruise_id to each dataset's name so merged entries are distinguishable."""
    tagged = []
    for d in datasets:
        dc = dict(d)
        dc["name"] = f"{d['name']} [{cruise_id}]"
        tagged.append(dc)
    return tagged


def _dedup_key(d: dict) -> tuple:
    """Key for deduplication: same data_type + doi means same dataset."""
    return (d.get("data_type"), d.get("doi"))


def merge_datasets(existing: list[dict], new_datasets: list[dict]) -> list[dict]:
    """
    Merge new_datasets into existing, avoiding duplicates by (data_type, doi).
    Entries without a DOI are merged by (data_type, name).
    """
    seen = {_dedup_key(d) for d in existing}
    result = list(existing)
    for d in new_datasets:
        k = _dedup_key(d)
        if k not in seen:
            seen.add(k)
            result.append(d)
    return result


# ── Patching ──────────────────────────────────────────────────────────────────

def clean_dataset(d: dict) -> dict:
    """Strip internal _* keys before writing to JSON."""
    return {k: v for k, v in d.items() if not k.startswith("_")}


def patch_paper(paper_id: str, new_datasets: list[dict], dry_run: bool) -> bool:
    path = PAPERS_DIR / f"{paper_id}.json"
    if not path.exists():
        print(f"  [skip] {paper_id} — file not found")
        return False

    paper = json.loads(path.read_text(encoding="utf-8"))
    old_data = paper.get("data") or []

    merged = merge_datasets(old_data, new_datasets)
    clean = [clean_dataset(d) for d in merged]

    added = len(clean) - len(old_data)
    print(f"  {paper_id}: {len(old_data)} -> {len(clean)} datasets (+{added})")

    if dry_run:
        if added:
            print(f"    [dry-run] would add:")
            for d in clean[len(old_data):]:
                print(f"      {d['data_type']:30s}  {d.get('doi','(no doi)')}")
        return True

    paper["data"] = clean
    path.write_text(json.dumps(paper, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cruise", help="Only process this cruise ID")
    args = ap.parse_args()

    cruises = [args.cruise] if args.cruise else list(CRUISE_PAPERS.keys())

    # Scrape each cruise once
    cruise_datasets: dict[str, list[dict]] = {}
    for cruise_id in cruises:
        if cruise_id not in CRUISE_PAPERS:
            print(f"Unknown cruise: {cruise_id}", file=sys.stderr)
            continue
        print(f"\n{'='*60}")
        print(f"Scraping {cruise_id}")
        print(f"{'='*60}")
        try:
            datasets = scrape_cruise(cruise_id)
            cruise_datasets[cruise_id] = datasets
            print(f"  Scraped {len(datasets)} datasets")
        except Exception as exc:
            print(f"  ERROR scraping {cruise_id}: {exc}", file=sys.stderr)
            cruise_datasets[cruise_id] = []
        time.sleep(1)

    # Build paper → merged datasets mapping
    # Papers used by multiple cruises get all datasets combined
    paper_datasets: dict[str, list[dict]] = {}
    for cruise_id, datasets in cruise_datasets.items():
        papers = CRUISE_PAPERS.get(cruise_id, [])
        # Tag datasets with cruise ID only when the same paper appears in multiple cruises
        multi_cruise_papers = {
            pid for pid, cruises_for_paper in
            {p: [c for c, ps in CRUISE_PAPERS.items() if p in ps] for p in papers}
            .items()
            if len(cruises_for_paper) > 1
        }
        for paper_id in papers:
            tagged = _tag_cruise(datasets, cruise_id) if paper_id in multi_cruise_papers else datasets
            if paper_id not in paper_datasets:
                paper_datasets[paper_id] = []
            paper_datasets[paper_id] = merge_datasets(paper_datasets[paper_id], tagged)

    # Patch papers
    print(f"\n{'='*60}")
    print("Patching papers")
    print(f"{'='*60}")
    patched = 0
    for paper_id, datasets in sorted(paper_datasets.items()):
        if patch_paper(paper_id, datasets, dry_run=args.dry_run):
            patched += 1

    mode = "dry-run" if args.dry_run else "patched"
    print(f"\nDone: {mode} {patched} papers across {len(cruise_datasets)} cruises.")


if __name__ == "__main__":
    main()
