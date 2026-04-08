"""
Extract additional metadata fields from pdf_text/*.txt files and update papers/*.json.

Fields extracted:
  acquisition.obs_spacing_km         – OBS/OBH instrument spacing
  acquisition.nearest_offset_m       – near-offset of streamer
  acquisition.frequency_range_hz     – [min, max] Hz bandpass
  acquisition.dominant_frequency_hz  – peak/dominant frequency
  acquisition.depth_penetration_km   – max imaging depth
  processing.migration_type          – Kirchhoff / PSTM / PSSDM / FD / etc.
  tectonic_setting                   – erosional / accretionary / mixed
  associated_earthquakes             – list of named rupture events
  data[].cdp_spacing_m               – CDP bin size per dataset
  location.seismic_lines[].depth_km  – max imaged depth per profile
  location.seismic_lines[].profile_orientation – margin-perpendicular / etc.

Usage:
  python -m src.extract.fields              # all papers
  python -m src.extract.fields paper_id1    # specific papers
"""

import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent.parent

# ── helpers ───────────────────────────────────────────────────────────────────

def _num(s: str) -> float:
    return float(s.replace(",", ".").replace(" ", ""))


def _clean(raw: str) -> str:
    """Remove control chars and collapse single newlines."""
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw)
    return re.sub(r"(?<!\n)\n(?!\n)", " ", text)


def _first(patterns, text) -> float | None:
    for pat, lo, hi in patterns:
        m = pat.search(text)
        if m:
            try:
                val = _num(m.group(1))
                if lo <= val <= hi:
                    return val
            except ValueError:
                continue
    return None


def _all_matches(patterns, text) -> list[float]:
    """Return all unique numeric matches (deduplicated, sorted)."""
    found = set()
    for pat, lo, hi in patterns:
        for m in pat.finditer(text):
            try:
                val = _num(m.group(1))
                if lo <= val <= hi:
                    found.add(val)
            except ValueError:
                continue
    return sorted(found)


# ── OBS spacing ───────────────────────────────────────────────────────────────

_OBS_PAT = [
    (re.compile(r'OBS[/H]*\s+(?:spacing|interval)\s+(?:of\s+)?[~∼≈]?\s*(\d+(?:[.,]\d+)?)\s*km\b', re.I), 0.5, 50),
    (re.compile(r'(\d+(?:[.,]\d+)?)\s*km\s+(?:OBS|OBH|station)\s+spacing', re.I), 0.5, 50),
    (re.compile(r'(?:placed|deployed|located)\s+(?:\w+\s+){0,4}(?:every|at\s+intervals\s+of)\s+(\d+(?:[.,]\d+)?)\s*km\b', re.I), 0.5, 50),
    (re.compile(r'nominal\s+spacing\s+of\s+(\d+(?:[.,]\d+)?)\s*km\b', re.I), 0.5, 50),
    (re.compile(r'station\s+spacing\s+(?:of\s+)?(\d+(?:[.,]\d+)?)\s*km\b', re.I), 0.5, 50),
]

# ── Nearest offset ────────────────────────────────────────────────────────────

_NEAR_PAT = [
    (re.compile(r'near(?:est)?\s+offset\s+(?:of\s+)?(\d+(?:[.,]\d+)?)\s*m\b', re.I), 10, 2000),
    (re.compile(r'minimum\s+offset\s+(?:of\s+)?(\d+(?:[.,]\d+)?)\s*m\b', re.I), 10, 2000),
    (re.compile(r'near\s+trace\s+(?:offset\s+)?(?:of\s+)?(\d+(?:[.,]\d+)?)\s*m\b', re.I), 10, 2000),
]

# ── Frequency range ───────────────────────────────────────────────────────────

_FREQ_RANGE_PAT = re.compile(
    r'(?:band[- ]?pass|filter(?:ed)?|frequency\s+range)[^\d]{0,30}'
    r'(\d+(?:[.,]\d+)?)\s*(?:to|[-–])\s*(\d+(?:[.,]\d+)?)\s*Hz\b',
    re.I,
)
_FREQ_RANGE_PAT2 = re.compile(
    r'(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*Hz\b',
    re.I,
)

# ── Dominant frequency ────────────────────────────────────────────────────────

_DOM_FREQ_PAT = [
    (re.compile(r'dominant\s+frequency\s+(?:of\s+)?[~∼≈]?\s*(\d+(?:[.,]\d+)?)\s*Hz\b', re.I), 1, 500),
    (re.compile(r'peak\s+frequency\s+(?:of\s+)?[~∼≈]?\s*(\d+(?:[.,]\d+)?)\s*Hz\b', re.I), 1, 500),
    (re.compile(r'center(?:ed)?\s+(?:at|around)\s+[~∼≈]?\s*(\d+(?:[.,]\d+)?)\s*Hz\b', re.I), 1, 500),
    (re.compile(r'(?:center|centre)\s+frequency\s+(?:of\s+)?[~∼≈]?\s*(\d+(?:[.,]\d+)?)\s*Hz\b', re.I), 1, 500),
]

# ── Depth penetration ─────────────────────────────────────────────────────────

_DEPTH_PAT = [
    (re.compile(r'(?:image[sd]?|penetrat(?:ion|e[sd]?)|imag(?:ing|e))\s+(?:to\s+)?(?:depth[s]?\s+of\s+)?[~∼≈]?\s*(\d+(?:[.,]\d+)?)\s*km\b', re.I), 5, 100),
    (re.compile(r'depth\s+(?:of\s+)?(?:penetration\s+of\s+)?[~∼≈]?\s*(\d+(?:[.,]\d+)?)\s*km\b', re.I), 5, 100),
    (re.compile(r'(?:resolve[sd]?|detected?)\s+(?:to\s+)?(?:depth[s]?\s+of\s+)?[~∼≈]?\s*(\d+(?:[.,]\d+)?)\s*km\b', re.I), 5, 100),
    (re.compile(r'(?:Moho|mantle|basement)\s+(?:\w+\s+){0,5}at\s+[~∼≈]?\s*(\d+(?:[.,]\d+)?)\s*km\b', re.I), 5, 100),
]

# ── Migration type ────────────────────────────────────────────────────────────

_MIGRATION_KEYWORDS = {
    "Kirchhoff": re.compile(r'Kirchhoff\s+(?:depth\s+|time\s+)?(?:pre[-\s]?stack\s+)?migrat', re.I),
    "PSTM": re.compile(r'(?:pre[-\s]?stack\s+time\s+migrat|PSTM)', re.I),
    "PSSDM": re.compile(r'(?:pre[-\s]?stack\s+(?:depth|migration)\s+(?:migrat|depth)|PSSDM|PSDM)', re.I),
    "FD": re.compile(r'(?:finite[- ]?difference\s+migrat|FD[-\s]migrat)', re.I),
    "TOPAS": re.compile(r'TOPAS', re.I),
    "post-stack": re.compile(r'post[-\s]?stack\s+(?:time\s+)?migrat', re.I),
    "f-k": re.compile(r'(?:f[-–]k\s+migrat|frequency[-\s]wavenumber\s+migrat)', re.I),
    "NMO": re.compile(r'NMO\s+(?:correction|stack)', re.I),
}

# ── Tectonic setting ──────────────────────────────────────────────────────────

_EROSIONAL = re.compile(r'\berosional\b', re.I)
_ACCRETIONARY = re.compile(r'\baccretion(?:ary)?\s+(?:prism|wedge|margin)\b', re.I)

# ── Associated earthquakes ────────────────────────────────────────────────────

_EQ_PATTERNS = [
    (re.compile(r'(?:200[4-9]|201\d|202\d)\s+M[wW]\s*[89]\.\d'), None),
    (re.compile(r'(?:1960|Valdivia)[^\w]*(?:M[wW]\s*9\.5|9\.5)?'), "Valdivia 1960 Mw9.5"),
    (re.compile(r'(?:2010|Maule)[^\w]*(?:M[wW]\s*8\.8|8\.8)?'), "Maule 2010 Mw8.8"),
    (re.compile(r'(?:2014|Iquique)[^\w]*(?:M[wW]\s*8\.2|8\.2)?'), "Iquique 2014 Mw8.2"),
    (re.compile(r'(?:2015|Illapel)[^\w]*(?:M[wW]\s*8\.3|8\.3)?'), "Illapel 2015 Mw8.3"),
    (re.compile(r'(?:2001|Arequipa)[^\w]*(?:M[wW]\s*8\.4|8\.4)?'), "Arequipa 2001 Mw8.4"),
    (re.compile(r'(?:1995|Antofagasta)[^\w]*(?:M[wW]\s*8\.0|8\.0)?'), "Antofagasta 1995 Mw8.0"),
    (re.compile(r'(?:2007|Tocopilla)[^\w]*(?:M[wW]\s*7\.7|7\.7)?'), "Tocopilla 2007 Mw7.7"),
]

_EQ_NAMED = {
    "Valdivia 1960 Mw9.5": re.compile(r'\b(?:1960|Valdivia)\b', re.I),
    "Maule 2010 Mw8.8": re.compile(r'\b(?:2010|Maule)\b(?![\w-])', re.I),
    "Iquique 2014 Mw8.2": re.compile(r'\b(?:2014|Iquique\s+earthquake)\b', re.I),
    "Illapel 2015 Mw8.3": re.compile(r'\b(?:2015|Illapel)\b', re.I),
    "Antofagasta 1995 Mw8.0": re.compile(r'\b(?:1995|Antofagasta\s+earthquake)\b', re.I),
    "Tocopilla 2007 Mw7.7": re.compile(r'\b(?:2007|Tocopilla\s+earthquake)\b', re.I),
}

# Use a more reliable approach: look for explicit Mw mentions
_EQ_MW = re.compile(r'M[wW]\s*([\d.]+)\s*(?:earthquake|event|rupture)?.{0,80}?(\d{4})', re.I)
_YEAR_MW = re.compile(r'(\d{4})\s+M[wW]\s*([\d.]+)', re.I)

_EQ_CATALOG = {
    ("1960", "9.5"): "Valdivia 1960 Mw9.5",
    ("2010", "8.8"): "Maule 2010 Mw8.8",
    ("2014", "8.2"): "Iquique 2014 Mw8.2",
    ("2015", "8.3"): "Illapel 2015 Mw8.3",
    ("1995", "8.0"): "Antofagasta 1995 Mw8.0",
    ("2001", "8.4"): "Arequipa 2001 Mw8.4",
    ("2007", "7.7"): "Tocopilla 2007 Mw7.7",
    ("2007", "7.9"): "Tocopilla 2007 Mw7.9",
}


def _extract_earthquakes(text: str) -> list[str]:
    found = set()
    for m in _YEAR_MW.finditer(text):
        year = m.group(1)
        mw_str = m.group(2)
        # Try exact match first
        key = (year, mw_str)
        if key in _EQ_CATALOG:
            found.add(_EQ_CATALOG[key])
        else:
            # Try rounding to 1 decimal
            try:
                mw = round(float(mw_str), 1)
                key2 = (year, str(mw))
                if key2 in _EQ_CATALOG:
                    found.add(_EQ_CATALOG[key2])
            except ValueError:
                pass
    return sorted(found)


# ── CDP spacing ───────────────────────────────────────────────────────────────

_CDP_PAT = [
    (re.compile(r'CDP\s+(?:bin\s+)?(?:spacing|interval|size)\s+(?:of\s+)?[~∼≈]?\s*(\d+(?:[.,]\d+)?)\s*m\b', re.I), 1, 200),
    (re.compile(r'(\d+(?:[.,]\d+)?)\s*m\s+CDP\s+(?:spacing|interval)', re.I), 1, 200),
    (re.compile(r'(?:bin|CMP)\s+size\s+(?:of\s+)?(\d+(?:[.,]\d+)?)\s*m\b', re.I), 1, 200),
    (re.compile(r'CMP\s+(?:spacing|interval)\s+(?:of\s+)?(\d+(?:[.,]\d+)?)\s*m\b', re.I), 1, 200),
]

# ── Profile depth / orientation ───────────────────────────────────────────────

_ORIENT_KEYWORDS = {
    "margin-perpendicular": re.compile(r'margin[- ]perpendicular|trench[- ]perpendicular|across[- ]strike', re.I),
    "margin-parallel": re.compile(r'margin[- ]parallel|trench[- ]parallel|along[- ]strike', re.I),
    "oblique": re.compile(r'oblique\s+(?:to\s+the\s+)?(?:margin|trench|strike)', re.I),
}


def _extract_orientation(text: str) -> str | None:
    for label, pat in _ORIENT_KEYWORDS.items():
        if pat.search(text):
            return label
    return None


# ── Frequency range extraction ────────────────────────────────────────────────

def _extract_freq_range(text: str) -> list[float] | None:
    for pat in [_FREQ_RANGE_PAT, _FREQ_RANGE_PAT2]:
        m = pat.search(text)
        if m:
            try:
                lo = _num(m.group(1))
                hi = _num(m.group(2))
                if 0.1 <= lo < hi <= 1000:
                    return [lo, hi]
            except ValueError:
                continue
    return None


# ── per-paper processing ──────────────────────────────────────────────────────

def process(paper_id: str) -> bool:
    txt_path = str(ROOT / "pdf_text" / f"{paper_id}.txt")
    json_path = str(ROOT / "papers" / f"{paper_id}.json")

    if not os.path.exists(txt_path) or not os.path.exists(json_path):
        print(f"SKIP {paper_id}: missing txt or json")
        return False

    with open(txt_path, encoding="utf-8") as f:
        text = _clean(f.read())

    with open(json_path, encoding="utf-8") as f:
        paper = json.load(f)

    changed = False
    changes = []

    # ── acquisition fields ────────────────────────────────────────────────
    acq = paper.get("acquisition")
    if acq is not None:
        for field, patterns in [
            ("obs_spacing_km", _OBS_PAT),
            ("nearest_offset_m", _NEAR_PAT),
        ]:
            if acq.get(field) is None:
                val = _first(patterns, text)
                if val is not None:
                    acq[field] = val
                    changes.append(f"{field}={val}")
                    changed = True

        if acq.get("depth_penetration_km") is None:
            val = _first(_DEPTH_PAT, text)
            if val is not None:
                acq["depth_penetration_km"] = val
                changes.append(f"depth_penetration_km={val}")
                changed = True

        if acq.get("frequency_range_hz") is None:
            freq = _extract_freq_range(text)
            if freq is not None:
                acq["frequency_range_hz"] = freq
                changes.append(f"frequency_range_hz={freq}")
                changed = True

    # ── processing fields ─────────────────────────────────────────────────
    proc = paper.get("processing")
    if proc is not None and proc.get("migration_type") is None:
        for mtype, pat in _MIGRATION_KEYWORDS.items():
            if pat.search(text):
                proc["migration_type"] = mtype
                changes.append(f"migration_type={mtype}")
                changed = True
                break

    # ── tectonic setting ──────────────────────────────────────────────────
    if paper.get("tectonic_setting") is None:
        has_erosional = bool(_EROSIONAL.search(text))
        has_accretionary = bool(_ACCRETIONARY.search(text))
        if has_erosional and has_accretionary:
            paper["tectonic_setting"] = "mixed"
            changes.append("tectonic_setting=mixed")
            changed = True
        elif has_erosional:
            paper["tectonic_setting"] = "erosional"
            changes.append("tectonic_setting=erosional")
            changed = True
        elif has_accretionary:
            paper["tectonic_setting"] = "accretionary"
            changes.append("tectonic_setting=accretionary")
            changed = True

    # ── associated earthquakes ────────────────────────────────────────────
    if not paper.get("associated_earthquakes"):
        eqs = _extract_earthquakes(text)
        if eqs:
            paper["associated_earthquakes"] = eqs
            changes.append(f"associated_earthquakes={eqs}")
            changed = True

    # ── CDP spacing for datasets ──────────────────────────────────────────
    cdp_val = _first(_CDP_PAT, text)
    if cdp_val is not None:
        for d in paper.get("data", []):
            if d.get("cdp_spacing_m") is None and d.get("data_type", "").upper() in ("MCS", "MCS_REFLECTION", "REFLECTION", "SEISMIC"):
                d["cdp_spacing_m"] = cdp_val
                changes.append(f"cdp_spacing_m={cdp_val} (dataset {d.get('name','?')})")
                changed = True
                break  # only first matching dataset

    # ── profile orientation (apply to all seismic lines if none set) ──────
    orientation = _extract_orientation(text)
    if orientation:
        loc = paper.get("location") or {}
        for sl in loc.get("seismic_lines", []):
            if sl.get("profile_orientation") is None:
                sl["profile_orientation"] = orientation
                changed = True
        if loc.get("seismic_lines"):
            changes.append(f"profile_orientation={orientation} (all lines)")

    if changed:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(paper, f, indent=2, ensure_ascii=False)
        print(f"OK  {paper_id}: {', '.join(changes)}")
    else:
        print(f"--- {paper_id}: nothing new")

    return changed


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ids = sys.argv[1:]
    if not ids:
        ids = [
            f[:-4]
            for f in sorted(os.listdir(ROOT / "pdf_text"))
            if f.endswith(".txt")
        ]

    updated = 0
    for pid in ids:
        if process(pid):
            updated += 1

    print(f"\nDone. {updated}/{len(ids)} papers updated.")
