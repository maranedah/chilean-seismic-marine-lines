#!/usr/bin/env python3
"""
_check_access.py — Resolve 'unknown'-access datasets by querying public repositories.

None of the 113 unknown datasets have a URL recorded.  This script discovers
candidate URLs by searching each repository's API using the paper's DOI, then
HEAD-verifies every candidate.  When a URL returns HTTP 2xx or 3xx it is
written back to the JSON with access='open'.

Strategy per repository type:
  PANGAEA  – searches the paper DOI via PANGAEA's search API
             (returns datasets that cite the paper)
  MGDS     – searches MGDS dataset registry by paper DOI
  IRIS     – checks FDSN station service for network codes found in dataset names
  others   – skipped; flagged in the report for manual review

Usage:
  python -m src.tools.check_access              # report only (no changes written)
  python -m src.tools.check_access --update     # patch JSONs in place
  python -m src.tools.check_access --paper ID   # single paper
  python -m src.tools.check_access --repo PANGAEA  # filter by repository type

Exit codes: 0 = success, 1 = at least one unrecoverable error.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

# Force UTF-8 output on Windows (dataset names contain degree signs, etc.)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Config ────────────────────────────────────────────────────────────────────

PAPERS_DIR = pathlib.Path(__file__).parent.parent.parent / "data" / "extracted_jsons"
EXCLUDE = {"survey_results.json", "data_availability.json", "schema.json"}
TIMEOUT = 12          # seconds per HTTP request
INTER_REQUEST_DELAY = 0.6   # courtesy delay between outbound calls

HEADERS = {
    "User-Agent": "chilean-seismic-access-checker/1.0 (research; non-commercial)",
    "Accept": "application/json",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _request(url: str, method: str = "GET") -> tuple[Optional[int], Optional[bytes]]:
    """Return (status_code, body_bytes) or (None, None) on connection failure."""
    try:
        req = Request(url, method=method, headers=HEADERS)
        with urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read() if method == "GET" else None
            return resp.status, body
    except HTTPError as exc:
        return exc.code, None
    except (URLError, OSError):
        return None, None


def head_ok(url: str) -> bool:
    """True if URL responds with 2xx or 3xx (i.e. reachable)."""
    status, _ = _request(url, method="HEAD")
    return status is not None and status < 400


def get_json(url: str) -> Optional[dict | list]:
    status, body = _request(url, method="GET")
    if status and status < 400 and body:
        try:
            return json.loads(body.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            return None
    return None


# ── Repository resolvers ──────────────────────────────────────────────────────

def resolve_pangaea(paper_doi: str) -> list[str]:
    """
    Return PANGAEA dataset URLs that cite *paper_doi*.

    PANGAEA search API: https://www.pangaea.de/api/find?q=...&count=20
    Each result that has a 'URI' pointing to doi.pangaea.de is a candidate.
    """
    if not paper_doi:
        return []
    q = quote(f'doi:"{paper_doi}"')
    data = get_json(f"https://www.pangaea.de/api/find?q={q}&count=20")
    time.sleep(INTER_REQUEST_DELAY)
    if not isinstance(data, dict):
        return []
    candidates: list[str] = []
    for hit in data.get("results", []):
        uri = hit.get("URI") or hit.get("uri") or ""
        if "pangaea.de" in uri and uri not in candidates:
            candidates.append(uri)
    return candidates


def resolve_mgds(paper_doi: str) -> list[str]:
    """
    Return MGDS dataset page URLs for datasets associated with *paper_doi*.

    MGDS exposes a REST endpoint: /tools/webservices/datasets.php?doi=...
    Returns a list of dataset objects with a 'uid' field; the browse URL is
    constructed as /tools/search/Files.php?data_set_uid=<uid>.
    """
    if not paper_doi:
        return []
    url = f"https://www.marine-geo.org/tools/webservices/datasets.php?doi={quote(paper_doi)}&format=json"
    data = get_json(url)
    time.sleep(INTER_REQUEST_DELAY)
    if not isinstance(data, list):
        return []
    candidates: list[str] = []
    for ds in data:
        uid = ds.get("uid") or ds.get("data_set_uid")
        if uid:
            browse = f"https://www.marine-geo.org/tools/search/Files.php?data_set_uid={uid}"
            if browse not in candidates:
                candidates.append(browse)
    return candidates


# Regex to find plausible FDSN network codes: 1–2 uppercase letters/digits
# that commonly appear in IRIS dataset names (e.g. "XW", "XX", "4C", "YH")
_NET_RE = re.compile(r'\b([A-Z][A-Z0-9])\b')


def resolve_iris(dataset_name: str) -> list[str]:
    """
    Try FDSN station service for network codes found in *dataset_name*.
    Returns IRIS MDA URLs for networks that respond with HTTP 200.
    """
    nets = list(dict.fromkeys(_NET_RE.findall(dataset_name)))  # unique, ordered
    candidates: list[str] = []
    for net in nets[:4]:
        fdsn = (
            f"http://service.iris.edu/fdsnws/station/1/query"
            f"?network={net}&level=network&format=text"
        )
        status, _ = _request(fdsn)
        time.sleep(INTER_REQUEST_DELAY)
        if status == 200:
            mda = f"http://ds.iris.edu/mda/{net}/"
            if mda not in candidates:
                candidates.append(mda)
    return candidates


# ── Repository type classifier ────────────────────────────────────────────────

def repo_type(repo: str) -> str:
    r = (repo or "").lower()
    if "pangaea" in r:
        return "pangaea"
    if "mgds" in r:
        return "mgds"
    if "iris" in r:
        return "iris"
    return "other"


# ── Paper loading / saving ────────────────────────────────────────────────────

def load_papers(paper_id: Optional[str] = None) -> list[tuple[pathlib.Path, dict]]:
    papers = []
    for f in sorted(PAPERS_DIR.glob("*.json")):
        if f.name in EXCLUDE:
            continue
        if paper_id and f.stem != paper_id:
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            papers.append((f, data))
        except Exception as exc:
            print(f"  [WARN] Could not load {f.name}: {exc}", file=sys.stderr)
    return papers


def save_paper(path: pathlib.Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Core logic ────────────────────────────────────────────────────────────────

def check_paper(
    path: pathlib.Path,
    data: dict,
    repo_filter: Optional[str],
    update: bool,
    verbose: bool,
) -> dict:
    """
    Check all unknown-access datasets in *data*.
    Returns a result dict summarising findings.
    """
    paper_id = data.get("id", path.stem)
    paper_doi = data.get("doi", "")
    datasets: list[dict] = data.get("data", [])

    unknown = [
        (i, d)
        for i, d in enumerate(datasets)
        if d.get("access") == "unknown"
    ]
    if not unknown:
        return {"paper": paper_id, "unknown": 0, "resolved": 0, "skipped": 0}

    resolved, skipped = 0, 0
    detail: list[str] = []

    # Cache API lookups per repo type so we call each API once per paper
    _cache: dict[str, list[str]] = {}

    def candidates_for(rtype: str, ds_name: str) -> list[str]:
        if rtype in _cache:
            return _cache[rtype]
        if rtype == "pangaea":
            urls = resolve_pangaea(paper_doi)
        elif rtype == "mgds":
            urls = resolve_mgds(paper_doi)
        elif rtype == "iris":
            urls = resolve_iris(ds_name)
        else:
            urls = []
        _cache[rtype] = urls
        return urls

    dirty = False

    for idx, ds in unknown:
        rtype = repo_type(ds.get("repository", ""))

        if repo_filter and rtype != repo_filter.lower():
            skipped += 1
            continue

        if rtype == "other":
            skipped += 1
            detail.append(f"  SKIP  [{ds.get('repository','')}] {ds.get('name','')[:60]}")
            continue

        candidates = candidates_for(rtype, ds.get("name", ""))

        found_url: Optional[str] = None
        for url in candidates:
            if head_ok(url):
                found_url = url
                break
            time.sleep(INTER_REQUEST_DELAY)

        if found_url:
            resolved += 1
            detail.append(f"  FOUND [{rtype.upper()}] {ds.get('name','')[:50]} -> {found_url}")
            if update:
                datasets[idx]["access"] = "open"
                datasets[idx]["url"] = found_url
                dirty = True
        else:
            skipped += 1
            hint = f"({len(candidates)} candidate(s) returned 4xx/timeout)" if candidates else "(no candidates from API)"
            detail.append(f"  MISS  [{rtype.upper()}] {ds.get('name','')[:50]}  {hint}")

    if dirty and update:
        save_paper(path, data)

    if verbose or resolved > 0:
        print(f"\n{'[UPDATED] ' if dirty else ''}Paper: {paper_id}  ({len(unknown)} unknown, {resolved} resolved)")
        for line in detail:
            print(line)

    return {
        "paper": paper_id,
        "unknown": len(unknown),
        "resolved": resolved,
        "skipped": skipped,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve unknown-access datasets by querying public repositories."
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Patch paper JSONs in place (default: report only)",
    )
    parser.add_argument(
        "--paper",
        metavar="ID",
        help="Check a single paper by ID (e.g. bangs_2020_basal_accretion_jgr)",
    )
    parser.add_argument(
        "--repo",
        metavar="TYPE",
        choices=["pangaea", "mgds", "iris"],
        help="Only check datasets whose repository matches TYPE",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print details for every paper, not just those with resolved datasets",
    )
    args = parser.parse_args()

    if args.update:
        print("Mode: UPDATE — JSONs will be patched in place")
    else:
        print("Mode: REPORT ONLY — pass --update to write changes")

    papers = load_papers(args.paper)
    if not papers:
        print("No matching papers found.", file=sys.stderr)
        return 1

    totals = {"unknown": 0, "resolved": 0, "skipped": 0, "papers_with_unknown": 0}
    errors = 0

    for path, data in papers:
        has_unknown = any(d.get("access") == "unknown" for d in data.get("data", []))
        if not has_unknown:
            continue
        totals["papers_with_unknown"] += 1
        try:
            result = check_paper(path, data, args.repo, args.update, args.verbose)
        except Exception as exc:
            print(f"  [ERROR] {path.stem}: {exc}", file=sys.stderr)
            errors += 1
            continue
        totals["unknown"] += result["unknown"]
        totals["resolved"] += result["resolved"]
        totals["skipped"] += result["skipped"]

    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary
  Papers with unknown datasets : {totals['papers_with_unknown']}
  Total unknown datasets        : {totals['unknown']}
  Resolved (URL found + 2xx)   : {totals['resolved']}
  Skipped / not found           : {totals['skipped']}
  Errors                        : {errors}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")

    if args.update and totals["resolved"] > 0:
        print(f"  {totals['resolved']} dataset(s) patched to access='open'.")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
