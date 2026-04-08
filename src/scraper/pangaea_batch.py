"""
pangaea_batch.py — Batch-patch papers with verified PANGAEA datasets.

Curated list based on DataCite API search (cruise codes) + manual relevance
verification (geographic location, data type, campaign metadata).

Excluded:
  - PANGAEA.931695  (SO107, Nicaragua, not Chile)
  - PANGAEA.974185  (SO161, radiocarbon ages — not geophysical)
  - PANGAEA.965599  (SO161, foraminifera — not geophysical)
  - PANGAEA.965600  (SO161, foraminifera — not geophysical)
  - PANGAEA.691407  (SO161, turbiditic sedimentology — not seismic acquisition)

Usage:
    python -m src.scraper.pangaea_batch --dry-run
    python -m src.scraper.pangaea_batch
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .pangaea import parse_pangaea_tab, to_dataset_entry, patch_paper

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PAPERS_DIR = Path(__file__).parent.parent.parent / "data" / "extracted_jsons"

# ---------------------------------------------------------------------------
# Curated DOI → paper ID mapping
# Each entry: doi (short form), papers (list of paper IDs to patch)
# ---------------------------------------------------------------------------

PANGAEA_DATASETS: list[dict] = [

    # ── SO104 + SO244 ────────────────────────────────────────────────────────
    # Note: 893033/893032 are collection-level DOIs (no Binary Size column);
    # data_type override avoids the unknown fallback.
    {
        "doi": "10.1594/PANGAEA.893033",
        "note": "Multibeam bathymetry from SONNE cruises SO104 and SO244 — north Chile",
        "data_type": "bathymetry",
        "papers": [
            # SO104 papers (north Chile — Antofagasta / Iquique / Valparaiso corridor)
            "contreras-reyes_2012_abrupt_dip_ngeo",
            "geersen_2015_seamounts_iquique",
            "geersen_2018_extensional_deformation_forearc_epsl",
            "geersen_2018_north_chile_active_tectonics",
            "sallaras_2005_antofagasta_erosion",
            "sallares_ranero_2006_seismic_images_springer",
            "storch_2021_iquique_seismic_images",
            "von_huene_ranero_2003_antofagasta_erosion_jgr",
            "von_huene_weinrebe_heeren_1999_north_chile_erosion",
            "zelt_1999_3d_tomography_chilean_margin_grl",
        ],
    },
    # 893034 excluded: parent/collection DOI, returns 400 for tab download.
    {
        "doi": "10.1594/PANGAEA.893032",
        "note": "Multibeam backscatter data from SONNE cruise SO244",
        "data_type": "backscatter",
        "papers": [
            "geersen_2018_extensional_deformation_forearc_epsl",
            "geersen_2018_north_chile_active_tectonics",
        ],
    },

    # ── SO244 / MGL1610 OBS ──────────────────────────────────────────────────
    {
        "doi": "10.1594/PANGAEA.929899",
        "note": "Long-term OBS experiment 12/2014-10/2016 offshore north Chile (SO244 deploy, MGL1610 recover)",
        "papers": [
            "geersen_2018_north_chile_active_tectonics",
            # MGL1610 papers that analyse the Iquique OBS seismicity
            "ma_2022_megathrust_reflectivity_iquique_natcomm",
            "olsen_2020_thick_sediment_epsl",
            "reginato_2020_iquique_wedge_tecto",
        ],
    },

    # ── SO297 (Copiapo — Warwel 2025) ────────────────────────────────────────
    {
        "doi": "10.1594/PANGAEA.968533",
        "note": "SO297 multibeam bathymetry raw data (Kongsberg EM 122)",
        "data_type": "bathymetry",
        "papers": ["warwel_2025_copiapo_refraction"],
    },
    {
        "doi": "10.1594/PANGAEA.968534",
        "note": "SO297 water column raw data (Kongsberg EM 122)",
        "data_type": "backscatter",
        "papers": ["warwel_2025_copiapo_refraction"],
    },
    {
        "doi": "10.1594/PANGAEA.969150",
        "note": "SO297 seismic processed data — OBS working area",
        "papers": ["warwel_2025_copiapo_refraction"],
    },
    {
        "doi": "10.1594/PANGAEA.969551",
        "note": "SO297 seismic processed data — OBH working area",
        "papers": ["warwel_2025_copiapo_refraction"],
    },
    {
        "doi": "10.1594/PANGAEA.969552",
        "note": "SO297 seismic processed data — onshore seismometer working area",
        "papers": ["warwel_2025_copiapo_refraction"],
    },
    {
        "doi": "10.1594/PANGAEA.984419",
        "note": "SO297 seismic processed data — OBH working area (v2)",
        "data_type": "seismic_refraction_obs",
        "papers": ["warwel_2025_copiapo_refraction"],
    },
    {
        "doi": "10.1594/PANGAEA.984420",
        "note": "SO297 seismic processed data — OBS working area (v2)",
        "data_type": "seismic_refraction_obs",
        "papers": ["warwel_2025_copiapo_refraction"],
    },
    {
        "doi": "10.1594/PANGAEA.984421",
        "note": "SO297 seismic processed data — onshore seismometer working area (v2)",
        "data_type": "seismic_refraction_obs",
        "papers": ["warwel_2025_copiapo_refraction"],
    },

    # ── JC23 ─────────────────────────────────────────────────────────────────
    {
        "doi": "10.1594/PANGAEA.782435",
        "note": "JC23 OBS/OBH seismic refraction profile P03, central Chile (~34°S)",
        "papers": [
            "klaucke_2012_cold_seeps_chile_margin_gml",
            "moscoso_2011_maule_wide_angle",
        ],
    },
]


def run(dry_run: bool = False) -> None:
    total_patched = 0
    total_skipped = 0

    for entry in PANGAEA_DATASETS:
        doi = entry["doi"]
        papers = entry["papers"]
        note = entry.get("note", "")
        print(f"\n{'='*65}")
        print(f"DOI : {doi}")
        print(f"Note: {note}")
        print(f"Papers ({len(papers)}): {', '.join(papers)}")

        # Verify all paper files exist before fetching
        missing = [p for p in papers if not (PAPERS_DIR / f"{p}.json").exists()]
        if missing:
            print(f"  WARNING: paper files not found — {missing}", file=sys.stderr)
            papers = [p for p in papers if p not in missing]

        if not papers:
            print("  No valid papers to patch — skipping DOI fetch.")
            continue

        # Fetch + parse PANGAEA tab
        try:
            meta = parse_pangaea_tab(doi)
            dataset_entry = to_dataset_entry(meta)
            # Apply per-entry overrides
            if "data_type" in entry:
                dataset_entry["data_type"] = entry["data_type"]
            # Use note as name fallback when tab parser couldn't extract a title
            if dataset_entry.get("name") == doi and entry.get("note"):
                dataset_entry["name"] = entry["note"]
            size_str = meta.get("_size_str", "?")
            n_files = meta.get("_file_count", "?")
            print(
                f"  data_type={dataset_entry['data_type']}  "
                f"size={size_str}  files={n_files}  "
                f"access={dataset_entry['access']}"
            )
        except Exception as exc:
            print(f"  ERROR fetching {doi}: {exc}", file=sys.stderr)
            total_skipped += len(papers)
            time.sleep(1)
            continue

        # Patch each paper
        for paper_id in papers:
            patch_paper(paper_id, dataset_entry, dry_run=dry_run)
            total_patched += 1

        time.sleep(0.5)   # be polite to PANGAEA

    print(f"\n{'='*65}")
    print(f"Done. Patched/attempted={total_patched}  skipped={total_skipped}")
    if dry_run:
        print("[dry-run] No files were modified.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Batch-patch papers with PANGAEA datasets")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would be done without writing any files")
    args = ap.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
