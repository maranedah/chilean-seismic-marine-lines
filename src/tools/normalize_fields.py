"""
Normalize vessel, source_type, and dataset format fields in all paper JSON files.
- vessel: string → list of canonical vessel names
- source_type: string → list of canonical source type names
- format (per dataset): string → list of canonical format names
"""
import json
import re
from pathlib import Path

PAPERS_DIR = Path(__file__).parent.parent.parent / "papers"
EXCLUDE = {"survey_results.json", "data_availability.json", "schema.json"}

# ── Vessel normalization ───────────────────────────────────────────────────────

VESSEL_PATTERNS = [
    ("R/V SONNE",                 re.compile(r"SONNE", re.I)),
    ("R/V Marcus G. Langseth",    re.compile(r"Langseth|MGL\d{4}", re.I)),
    ("R/V Conrad",                re.compile(r"R/V Conrad|\bConrad\b", re.I)),
    ("R/V Polar Duke",            re.compile(r"Polar Duke", re.I)),
    ("R/V Yaquina",               re.compile(r"Yaquina", re.I)),
    ("R/V Melville",              re.compile(r"R/V Melville|\bMelville\b", re.I)),
    ("JOIDES Resolution",         re.compile(r"JOIDES Resolution", re.I)),
    ("JAMSTEC vessel",            re.compile(r"JAMSTEC|Japanese research vessel", re.I)),
    ("French research vessel",    re.compile(r"French research vessel", re.I)),
    ("Land-based network",        re.compile(r"Land-based|Land and offshore|land stations", re.I)),
]


def extract_vessels(raw: str | list | None) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw  # already normalized
    found = []
    for name, pat in VESSEL_PATTERNS:
        if pat.search(raw):
            found.append(name)
    if not found:
        # Fallback: strip parenthetical notes and return as-is
        clean = re.sub(r"\([^)]*\)", "", raw).strip().rstrip(",").strip()
        clean = re.sub(r"\s+", " ", clean)
        if clean:
            found.append(clean)
    return found or None


# ── Source-type normalization ─────────────────────────────────────────────────

# Order matters: check more-specific patterns first
SOURCE_PATTERNS = [
    ("sub-bottom profiler",    re.compile(r"PARASOUND|sub-?bottom profiler|subbottom profiler", re.I)),
    ("multibeam echosounder",  re.compile(r"multibeam echosounder|multibeam", re.I)),
    ("explosive shots",        re.compile(r"explosive shots", re.I)),
    ("passive seismic",        re.compile(r"passive seismic|passive OBS|passive \(|passive$", re.I)),
    ("airgun array",           re.compile(r"airgun|air-gun|reflection seismic", re.I)),
    ("sparker",                re.compile(r"sparker", re.I)),
    ("boomer",                 re.compile(r"boomer", re.I)),
    ("single-channel seismic", re.compile(r"single-channel seismic", re.I)),
    ("drilling",               re.compile(r"drilling \(ODP\)|ODP Leg", re.I)),
]

# Remove duplicates introduced by combined patterns, preserving order
def extract_source_types(raw: str | list | None) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw  # already normalized
    found: list[str] = []
    for name, pat in SOURCE_PATTERNS:
        if pat.search(raw) and name not in found:
            found.append(name)
    if not found:
        clean = re.sub(r"\([^)]*\)", "", raw).strip()
        if clean:
            found.append(clean)
    return found or None


# ── Format normalization ──────────────────────────────────────────────────────

FORMAT_MAP: dict[str, str] = {
    "SEG-Y": "SEG-Y",
    "SEGY": "SEG-Y",
    "SGY": "SEG-Y",
    "SEGD": "SEG-D",
    "SEG-D": "SEG-D",
    "NetCDF": "NetCDF",
    "ASCII": "ASCII",
    "CSV": "CSV",
    "miniSEED": "miniSEED",
    "MSEED": "miniSEED",
    "SEED": "SEED",
    "GeoTIFF": "GeoTIFF",
    "XTF": "XTF",
    "KEB": "KEB",
    "R2R:Nav": "R2R:Nav",
    "Kongsberg .all": "Kongsberg .all",
}

# Strings that appear after "/" but are NOT format names
_FORMAT_SKIP = re.compile(
    r"^(paper sections?|model output|raw shots.*|note:.*|processed.*)$", re.I
)


def _normalize_format_token(token: str) -> str | None:
    """Strip notes in parens, then look up in FORMAT_MAP."""
    clean = re.sub(r"\([^)]*\)", "", token).strip()
    # Exact match (case-insensitive)
    for key, canonical in FORMAT_MAP.items():
        if clean.lower() == key.lower():
            return canonical
    # Partial match for known formats embedded in longer strings
    # e.g. "ASCII (LDS NMEA)" already handled by paren strip
    return None


def extract_formats(raw: str | list | None) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw  # already normalized
    # Split on " / " or "/"
    parts = re.split(r"\s*/\s*", raw)
    result: list[str] = []
    for part in parts:
        part = part.strip()
        if _FORMAT_SKIP.match(part):
            continue
        canonical = _normalize_format_token(part)
        if canonical and canonical not in result:
            result.append(canonical)
    if not result:
        # Fallback: strip parens and return cleaned string
        clean = re.sub(r"\([^)]*\)", "", raw).strip()
        if clean:
            result.append(clean)
    return result or None


# ── Main ──────────────────────────────────────────────────────────────────────

def process_file(path: Path) -> bool:
    """Return True if the file was modified."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    changed = False

    # Vessel
    acq = data.get("acquisition")
    if acq and "vessel" in acq:
        raw = acq["vessel"]
        normalized = extract_vessels(raw)
        if normalized != raw:
            acq["vessel"] = normalized
            changed = True

    # Source type
    if acq and "source_type" in acq:
        raw = acq["source_type"]
        normalized = extract_source_types(raw)
        if normalized != raw:
            acq["source_type"] = normalized
            changed = True

    # Format (per dataset)
    for ds in data.get("data", []):
        if "format" in ds and ds["format"] is not None:
            raw = ds["format"]
            normalized = extract_formats(raw)
            if normalized != raw:
                ds["format"] = normalized
                changed = True

    if changed:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        print(f"  updated: {path.name}")

    return changed


def main() -> None:
    files = sorted(f for f in PAPERS_DIR.glob("*.json") if f.name not in EXCLUDE)
    updated = sum(1 for f in files if process_file(f))
    print(f"\nDone — {updated}/{len(files)} files updated.")


if __name__ == "__main__":
    main()
