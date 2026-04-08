"""
Extract seismic acquisition resolution parameters from pdf_text/*.txt files
and update the corresponding papers/*.json files.

Fields populated in acquisition{}:
  shot_interval_m   – shot point interval in metres
  group_interval_m  – receiver group interval / channel spacing in metres

Usage:
  python -m src.extract.resolution              # all papers
  python -m src.extract.resolution paper_id1    # specific papers
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent

# ── regex helpers ─────────────────────────────────────────────────────────────

def _num(s: str) -> float:
    """Convert a string number (possibly with comma) to float."""
    return float(s.replace(",", "."))


# Shot-point interval patterns (metres)
_SHOT_PATTERNS = [
    # "shot interval of 50 m"  /  "shot-point interval of 50 m"
    re.compile(
        r'shot[- ]?(?:point[- ]?)?interval[s]?\s+(?:of\s+)?(\d+(?:[.,]\d+)?)\s*m\b',
        re.IGNORECASE,
    ),
    # "50 m shot spacing"
    re.compile(
        r'(\d+(?:[.,]\d+)?)\s*m\s+shot\s+(?:point\s+)?(?:interval|spacing)',
        re.IGNORECASE,
    ),
    # "shot spacing of 50 m"
    re.compile(
        r'shot\s+(?:point\s+)?spacing\s+(?:of\s+)?(\d+(?:[.,]\d+)?)\s*m\b',
        re.IGNORECASE,
    ),
    # "SPI = 50 m" or "SPI of 50 m"
    re.compile(
        r'\bSPI\s*(?:=|of|:)\s*(\d+(?:[.,]\d+)?)\s*m\b',
        re.IGNORECASE,
    ),
    # "fired every 50 m"  /  "triggered every 50 m"
    re.compile(
        r'(?:fired|triggered|shot)\s+every\s+(\d+(?:[.,]\d+)?)\s*m\b',
        re.IGNORECASE,
    ),
    # "airgun ... every 50 m" — loose pattern
    re.compile(
        r'(?:airgun|source)\s+(?:\w+\s+){0,4}every\s+(\d+(?:[.,]\d+)?)\s*m\b',
        re.IGNORECASE,
    ),
    # "shot spacing of ~150 m" or "shot spacing of ∼150 m" (with tilde/approx)
    re.compile(
        r'shot\s+(?:point\s+)?spacing\s+(?:of\s+)?[~∼≈]?\s*(\d+(?:[.,]\d+)?)\s*m\b',
        re.IGNORECASE,
    ),
    # "shots were recorded every 125 m" / "shots ... every N m"
    re.compile(
        r'shots?\s+(?:\w+\s+){0,3}every\s+[~∼≈]?\s*(\d+(?:[.,]\d+)?)\s*m\b',
        re.IGNORECASE,
    ),
    # "every N m along" or "every N–M m" (take lower bound of range)
    re.compile(
        r'fired\s+(?:\w+\s+){0,3}every\s+[~∼≈]?\s*(\d+(?:[.,]\d+)?)(?:[–\-]\d+)?\s*m\b',
        re.IGNORECASE,
    ),
]

# Group / receiver interval patterns (metres)
_GROUP_PATTERNS = [
    # "group interval of 12.5 m"
    re.compile(
        r'group\s+interval[s]?\s+(?:of\s+)?(\d+(?:[.,]\d+)?)\s*m\b',
        re.IGNORECASE,
    ),
    # "12.5 m group interval"
    re.compile(
        r'(\d+(?:[.,]\d+)?)\s*m\s+group\s+interval',
        re.IGNORECASE,
    ),
    # "group spacing of 12.5 m"
    re.compile(
        r'group\s+spacing\s+(?:of\s+)?(\d+(?:[.,]\d+)?)\s*m\b',
        re.IGNORECASE,
    ),
    # "receiver spacing of 12.5 m"
    re.compile(
        r'receiver\s+(?:group\s+)?spacing\s+(?:of\s+)?(\d+(?:[.,]\d+)?)\s*m\b',
        re.IGNORECASE,
    ),
    # "channel spacing of 12.5 m"
    re.compile(
        r'channel\s+spacing\s+(?:of\s+)?(\d+(?:[.,]\d+)?)\s*m\b',
        re.IGNORECASE,
    ),
    # "trace spacing of 6.25 m"
    re.compile(
        r'trace\s+spacing\s+(?:of\s+)?(\d+(?:[.,]\d+)?)\s*m\b',
        re.IGNORECASE,
    ),
    # "12.5-m group interval" (hyphenated)
    re.compile(
        r'(\d+(?:[.,]\d+)?)-m\s+group\s+interval',
        re.IGNORECASE,
    ),
    # "hydrophone spacing of 12.5 m"
    re.compile(
        r'hydrophone\s+spacing\s+(?:of\s+)?(\d+(?:[.,]\d+)?)\s*m\b',
        re.IGNORECASE,
    ),
    # "receivers spaced every 12.5 m" / "receivers spaced at 12.5 m"
    re.compile(
        r'receivers?\s+spaced\s+(?:every|at)\s+[~∼≈]?\s*(\d+(?:[.,]\d+)?)\s*m\b',
        re.IGNORECASE,
    ),
    # "each N m apart" (receiver stations)
    re.compile(
        r'(?:stations?|receivers?)\s+(?:\w+\s+){0,3}each\s+(\d+(?:[.,]\d+)?)\s*m\s+apart\b',
        re.IGNORECASE,
    ),
]


def _first_match(patterns, text) -> float | None:
    """Return the first numeric match from a list of compiled patterns."""
    for pat in patterns:
        m = pat.search(text)
        if m:
            try:
                val = _num(m.group(1))
                # Sanity bounds: 1–500 m is reasonable for any seismic spacing
                if 1 <= val <= 500:
                    return val
            except ValueError:
                continue
    return None


# ── per-paper processing ──────────────────────────────────────────────────────

def process(paper_id: str) -> dict:
    txt_path = str(ROOT / "data" / "extracted_text" / f"{paper_id}.txt")
    json_path = str(ROOT / "data" / "extracted_jsons" / f"{paper_id}.json")

    result = {"shot_interval_m": None, "group_interval_m": None, "changed": False}

    if not os.path.exists(txt_path):
        print(f"SKIP {paper_id}: no txt file")
        return result
    if not os.path.exists(json_path):
        print(f"SKIP {paper_id}: no json file")
        return result

    with open(txt_path, encoding="utf-8") as f:
        raw = f.read()
    # Strip PDF-extraction control characters (e.g. \x01 ligature markers)
    # but keep newlines and tabs
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)
    # Collapse single newlines within paragraphs so patterns can span line breaks
    # (keep double newlines as paragraph breaks)
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)

    shot = _first_match(_SHOT_PATTERNS, text)
    group = _first_match(_GROUP_PATTERNS, text)

    with open(json_path, encoding="utf-8") as f:
        paper = json.load(f)

    acq = paper.get("acquisition")
    if acq is None:
        print(f"SKIP {paper_id}: no acquisition block")
        return result

    changed = False
    for field, val in [("shot_interval_m", shot), ("group_interval_m", group)]:
        if val is not None and acq.get(field) is None:
            acq[field] = val
            changed = True

    if changed:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(paper, f, indent=2, ensure_ascii=False)
        print(f"OK  {paper_id}: shot={shot} m, group={group} m")
    else:
        print(f"--- {paper_id}: shot={shot} m, group={group} m (no change needed)")

    result.update({"shot_interval_m": shot, "group_interval_m": group, "changed": changed})
    return result


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Extract shot/group interval parameters from PDF text files")
    parser.add_argument("paper_ids", nargs="*", metavar="PAPER_ID",
                        help="Paper IDs to process (default: all with extracted text)")
    args = parser.parse_args()

    ids = args.paper_ids
    if not ids:
        ids = [
            f[:-4]
            for f in sorted(os.listdir(ROOT / "data" / "extracted_text"))
            if f.endswith(".txt")
        ]

    updated = 0
    for pid in ids:
        r = process(pid)
        if r["changed"]:
            updated += 1

    print(f"\nDone. {updated}/{len(ids)} papers updated.")


if __name__ == "__main__":
    main()
