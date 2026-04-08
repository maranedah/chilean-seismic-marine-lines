"""
download_pdfs.py — Chilean Marine Seismic Lines PDF downloader

Downloads PDF copies of papers listed in the JSON database.

Strategy (in order):
  1. Use open_access_url from the paper JSON if set, and resolve to a
     direct PDF link where possible (follows DOI redirects, scrapes OceanRep
     pages, converts Nature/Elsevier article pages to PDF URLs).
  2. Query the Unpaywall API for a legal open-access PDF (requires --email).
  3. Skip if no open-access version found.

PDFs are saved as  pdfs/{paper_id}.pdf  (already-existing files are skipped).

Usage:
    python -m src.downloader.pdfs --all --email you@example.com
    python -m src.downloader.pdfs --all --dry-run
    python -m src.downloader.pdfs --paper bangs_2020_basal_accretion_jgr --email you@example.com
"""

import argparse
import io
import json
import re
import sys
import time

# Force UTF-8 output on Windows (titles contain degree signs, prime symbols, etc.)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

import requests

PAPERS_DIR = Path(__file__).parent.parent.parent / "data" / "extracted_jsons"
PDFS_DIR = Path(__file__).parent.parent.parent / "data" / "source_paper_pdfs"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Initialized in main() to avoid creating an HTTP connection pool at import time.
SESSION: requests.Session


# ---------------------------------------------------------------------------
# Publisher-aware session warm-up
# ---------------------------------------------------------------------------

def _article_page_for_pdf(pdf_url: str, paper: dict) -> str | None:
    """Return the article landing page URL that should be visited before
    downloading *pdf_url* so the publisher's CDN sets the required cookies."""
    u = pdf_url.lower()

    # OUP / GJI: article-pdf/VOL/ISSUE/PAGE/ID/file.pdf  →  article/VOL/ISSUE/PAGE/ID
    import re
    oup_m = re.match(
        r"(https://academic\.oup\.com/[^/]+)/article-pdf/(.+?)(/[^/]+\.pdf)?$",
        pdf_url,
        re.IGNORECASE,
    )
    if oup_m:
        return f"{oup_m.group(1)}/article/{oup_m.group(2)}"

    # Wiley pdfdirect → use the paper's own URL or construct from DOI
    if "onlinelibrary.wiley.com/doi/pdfdirect/" in pdf_url:
        paper_url = paper.get("url") or ""
        if "onlinelibrary.wiley.com" in paper_url:
            return paper_url
        doi = paper.get("doi", "")
        if doi:
            return f"https://onlinelibrary.wiley.com/doi/abs/{doi}"

    # AGU pdfdirect
    if "agupubs.onlinelibrary.wiley.com/doi/pdfdirect/" in pdf_url:
        paper_url = paper.get("url") or ""
        if "agupubs.onlinelibrary.wiley.com" in paper_url:
            return paper_url
        doi = paper.get("doi", "")
        if doi:
            return f"https://agupubs.onlinelibrary.wiley.com/doi/abs/{doi}"

    # GeoSphere (silverchair / pubs.geoscienceworld.org)
    gso_m = re.match(
        r"(https://pubs\.geoscienceworld\.org/[^/]+/[^/]+)/article-pdf/(.+?)(/[^/]+\.pdf)?$",
        pdf_url,
        re.IGNORECASE,
    )
    if gso_m:
        return f"{gso_m.group(1)}/article/{gso_m.group(2)}"

    return None


def warm_up_session(pdf_url: str, paper: dict) -> None:
    """Visit the article landing page to acquire session cookies and prime
    the Referer header before the actual PDF download."""
    article_url = _article_page_for_pdf(pdf_url, paper)
    if not article_url:
        return
    try:
        SESSION.get(
            article_url,
            timeout=20,
            allow_redirects=True,
            headers={"Referer": "https://www.google.com/"},
        )
        SESSION.headers["Referer"] = article_url
        time.sleep(0.8)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Paper loading
# ---------------------------------------------------------------------------

def load_papers() -> list[dict]:
    exclude = {"survey_results.json", "data_availability.json", "schema.json"}
    papers = []
    for f in sorted(PAPERS_DIR.glob("*.json")):
        if f.name in exclude:
            continue
        with open(f, encoding="utf-8") as fh:
            papers.append(json.load(fh))
    return papers


# ---------------------------------------------------------------------------
# URL resolution helpers
# ---------------------------------------------------------------------------

def is_direct_pdf_url(url: str) -> bool:
    """Heuristic: does this URL likely serve a PDF directly (no JS needed)?"""
    u = url.lower()
    return (
        u.endswith(".pdf")
        or "/pdfdirect/" in u
        or "/article-pdf/" in u
        or (u.endswith("/pdf") and "mdpi.com" in u)
    )


def resolve_oceanrep(url: str) -> str | None:
    """Scrape an OceanRep eprint page for the direct PDF file link."""
    try:
        r = SESSION.get(url, timeout=20)
        # PDF links look like: /id/eprint/NNN/1/filename.pdf
        match = re.search(r'href="(/id/eprint/\d+/\d+/[^"]+\.pdf)"', r.text)
        if match:
            return "https://oceanrep.geomar.de" + match.group(1)
        # Also try: href="...eprint/NNN/filename.pdf"
        match = re.search(r'"(https://oceanrep\.geomar\.de[^"]+\.pdf)"', r.text)
        if match:
            return match.group(1)
    except Exception as exc:
        print(f"    [WARN] OceanRep scrape failed: {exc}")
    return None


def resolve_elsevier_am(url: str) -> str | None:
    """
    Elsevier accepted-manuscript URL (/science/article/am/pii/XXXX).
    Try the /pdf suffix; Elsevier sometimes serves the AM PDF there.
    """
    pdf_url = url.rstrip("/") + "/pdf"
    try:
        r = SESSION.head(pdf_url, timeout=15, allow_redirects=True)
        if "pdf" in r.headers.get("Content-Type", "").lower():
            return pdf_url
        # If 200 or redirect, optimistically return it — download will validate
        if r.status_code in (200, 301, 302):
            return pdf_url
    except Exception:
        pass
    # Fallback: return the original URL and let the downloader check magic bytes
    return url


def resolve_nature_page(url: str) -> str | None:
    """Nature article page -> try appending .pdf (works for open-access articles)."""
    pdf_url = url.rstrip("/") + ".pdf"
    try:
        r = SESSION.head(pdf_url, timeout=15, allow_redirects=True)
        ct = r.headers.get("Content-Type", "").lower()
        if "pdf" in ct or r.status_code in (200, 301, 302):
            return pdf_url
    except Exception:
        pass
    return None


def resolve_doi_redirect(url: str) -> str | None:
    """Follow a doi.org redirect and extract a usable PDF URL from the landing page."""
    try:
        r = SESSION.get(url, timeout=20, allow_redirects=True)
        final = r.url

        if is_direct_pdf_url(final):
            return final

        # AGU/Wiley article page — convert to pdfdirect
        agu_m = re.match(
            r"https?://agupubs\.onlinelibrary\.wiley\.com/doi/(10\.[^?#\s]+)", final
        )
        if agu_m and "/pdfdirect/" not in final:
            return f"https://agupubs.onlinelibrary.wiley.com/doi/pdfdirect/{agu_m.group(1)}"

        # AGU/Wiley: look for pdfdirect href in the HTML
        match = re.search(r'https://[^"\'<>\s]+/pdfdirect/[^"\'<>\s]+', r.text)
        if match:
            return match.group(0)

        # Nature OA: try appending .pdf
        if re.match(r"https?://www\.nature\.com/articles/", final):
            candidate = final.rstrip("/") + ".pdf"
            return candidate

        # Elsevier AM
        if "sciencedirect.com/science/article/am/pii/" in final:
            return resolve_elsevier_am(final)

        # Return final landing page as fallback; downloader will check magic bytes
        return final
    except Exception as exc:
        print(f"    [WARN] DOI resolve failed: {exc}")
    return None


def resolve_pdf_url(raw_url: str) -> str | None:
    """
    Given any open_access_url value, return a URL that should serve a PDF
    (directly downloadable), or None if we cannot determine one.
    """
    url = raw_url.strip()

    if is_direct_pdf_url(url):
        return url

    if "oceanrep.geomar.de/id/eprint/" in url and url.endswith("/"):
        return resolve_oceanrep(url)

    if "sciencedirect.com/science/article/am/pii/" in url:
        return resolve_elsevier_am(url)

    if re.match(r"https?://www\.nature\.com/articles/", url) and not url.endswith(".pdf"):
        return resolve_nature_page(url) or url

    if url.startswith("https://doi.org/") or url.startswith("http://doi.org/"):
        return resolve_doi_redirect(url)

    # AGU/Wiley article page (not already a pdfdirect URL) — convert to pdfdirect
    agu_match = re.match(
        r"https?://agupubs\.onlinelibrary\.wiley\.com/doi/(10\.[^?#\s]+)", url
    )
    if agu_match and "/pdfdirect/" not in url:
        doi_part = agu_match.group(1)
        return f"https://agupubs.onlinelibrary.wiley.com/doi/pdfdirect/{doi_part}"

    # Andean Geology viewer page — convert /view/ to /download/
    if "andeangeology.cl" in url and "/article/view/" in url:
        return url.replace("/article/view/", "/article/download/")

    # Elsevier linkinghub resolver — follow redirect then handle
    if "linkinghub.elsevier.com/retrieve/" in url:
        try:
            r = SESSION.get(url, timeout=20, allow_redirects=True)
            final = r.url
            if "sciencedirect.com/science/article/am/pii/" in final:
                return resolve_elsevier_am(final)
            return final
        except Exception:
            pass

    # Unknown pattern — try as-is
    return url


# ---------------------------------------------------------------------------
# Unpaywall
# ---------------------------------------------------------------------------

def get_unpaywall_pdf(doi: str, email: str) -> str | None:
    """Query Unpaywall for the best legal open-access PDF URL."""
    try:
        r = SESSION.get(
            f"https://api.unpaywall.org/v2/{doi}",
            params={"email": email},
            timeout=15,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        loc = data.get("best_oa_location") or {}
        return loc.get("url_for_pdf") or loc.get("url_for_landing_page")
    except Exception as exc:
        print(f"    [WARN] Unpaywall error: {exc}")
    return None


# ---------------------------------------------------------------------------
# Downloading
# ---------------------------------------------------------------------------

def download_pdf(url: str, dest: Path, dry_run: bool, paper: dict | None = None) -> bool:
    """Stream a PDF from url to dest. Returns True on success."""
    if dest.exists():
        print(f"  [EXISTS] {dest.name}")
        return True

    if dry_run:
        print(f"  [DRY-RUN] -> {dest.name}")
        return True

    # Visit the article landing page first for publishers that require session cookies
    if paper is not None:
        warm_up_session(url, paper)

    # Some legacy academic servers (e.g. ODP/TAMU) have outdated SSL certs
    verify = "www-odp.tamu.edu" not in url

    try:
        r = SESSION.get(
            url,
            timeout=60,
            stream=True,
            allow_redirects=True,
            verify=verify,
            headers={"Accept": "application/pdf,*/*;q=0.9"},
        )
        r.raise_for_status()

        # Validate we actually got a PDF (check Content-Type or magic bytes)
        ct = r.headers.get("Content-Type", "").lower()
        chunks = r.iter_content(65536)
        first = next(chunks, b"")

        if "pdf" not in ct and "octet-stream" not in ct:
            if not first.startswith(b"%PDF"):
                print(f"  [SKIP] Not a PDF (Content-Type: {ct.split(';')[0]})")
                return False

        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            f.write(first)
            for chunk in chunks:
                f.write(chunk)

        size_kb = dest.stat().st_size // 1024
        print(f"  [OK] {dest.name}  ({size_kb} KB)")
        return True

    except requests.HTTPError as e:
        print(f"  [ERROR] HTTP {e.response.status_code}  {url[:80]}")
    except requests.RequestException as e:
        print(f"  [ERROR] {e}")
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    global SESSION
    SESSION = requests.Session()
    SESSION.headers.update(HEADERS)

    parser = argparse.ArgumentParser(
        description="Download PDF copies of Chilean marine seismic papers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Process all papers")
    group.add_argument("--paper", metavar="ID", help="Process one paper by ID")

    parser.add_argument(
        "--email",
        metavar="EMAIL",
        help="Your email for Unpaywall API — enables fallback OA lookup for papers without open_access_url",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading",
    )
    parser.add_argument(
        "--output",
        metavar="DIR",
        default=str(PDFS_DIR),
        help=f"Output directory (default: {PDFS_DIR})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        metavar="SEC",
        help="Seconds to wait between downloads (default: 1.5)",
    )

    args = parser.parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    papers = load_papers()
    if args.paper:
        papers = [p for p in papers if p["id"] == args.paper]
        if not papers:
            print(f"Paper '{args.paper}' not found.")
            sys.exit(1)

    ok = skipped = failed = 0

    for paper in papers:
        pid = paper["id"]
        doi = paper.get("doi", "")
        oa_url = paper.get("open_access_url")
        dest = output_dir / f"{pid}.pdf"

        print(f"[{paper['year']}] {paper['title'][:78]}")
        print(f"  id : {pid}")

        if dest.exists() and not args.dry_run:
            print(f"  [EXISTS] {dest.name}")
            ok += 1
            print()
            continue

        pdf_url = None
        source = None

        # 1. open_access_url from JSON
        if oa_url:
            pdf_url = resolve_pdf_url(oa_url)
            if pdf_url:
                source = "open_access_url"

        # 2. Unpaywall fallback
        if not pdf_url and doi and args.email:
            print(f"  -> Querying Unpaywall...")
            pdf_url = get_unpaywall_pdf(doi, args.email)
            if pdf_url:
                source = "unpaywall"
            time.sleep(1.0)  # Unpaywall rate-limit courtesy

        if not pdf_url:
            print(f"  [SKIP] No open-access PDF found")
            skipped += 1
            print()
            continue

        print(f"  -> {source}: {pdf_url[:90]}")
        if download_pdf(pdf_url, dest, args.dry_run, paper=paper):
            ok += 1
        else:
            failed += 1

        if not args.dry_run:
            time.sleep(args.delay)
        print()

    print("=== PDF Download Summary ===")
    print(f"  Downloaded / already exist : {ok}")
    print(f"  Skipped (no OA found)      : {skipped}")
    print(f"  Failed (error)             : {failed}")
    print(f"  Output directory           : {output_dir}")


if __name__ == "__main__":
    main()
