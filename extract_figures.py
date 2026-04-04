"""
extract_figures.py — Crop figure+caption regions from a paper PDF

Strategy:
  1. Extract all text from the PDF and find every "Figure N" caption regardless
     of which page it appears on.
  2. For each embedded raster image, locate its bounding box on the page and
     determine which Figure N it belongs to (by searching nearby text on the
     same page for a figure label, falling back to document order).
  3. Group all sub-panel rects that share the same figure label, compute the
     UNION bounding rect, and render one combined crop per figure.

Usage:
    python extract_figures.py PAPER_ID [--dpi N] [--padding N] [--output-dir DIR]

Outputs:
    images/{paper_id}/fig_NNN.png        — one crop per figure (named by figure number)
    images/{paper_id}/_manifest.json     — figure inventory with full captions
"""

import argparse
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PDFS_DIR = Path(__file__).parent / "pdfs"
IMAGES_DIR = Path(__file__).parent / "images"

# Regex to find figure labels anywhere in the text.
# Matches: Figure 1, Figure 1a, Fig. 2, Figure S1, etc.
FIGURE_LABEL_RE = re.compile(
    r"(?:Figure|FIGURE|Fig\.?)\s+"
    r"([0-9]+[a-zA-Z]?)"          # number, optionally followed by a letter
    r"[\s\|\.\u2013\-:]+",        # separator (space, pipe, dash, colon)
    re.UNICODE,
)


def extract_all_captions(doc) -> dict[str, str]:
    """
    Scan full PDF text and return a dict mapping figure label -> caption text.
    e.g. {"1": "Map of northern Chile...", "2": "MCS profiles..."}
    """
    full_text = "\n".join(page.get_text("text") for page in doc)

    captions: dict[str, str] = {}
    for m in FIGURE_LABEL_RE.finditer(full_text):
        label = m.group(1)
        start = m.end()
        next_m = FIGURE_LABEL_RE.search(full_text, start)
        end = min(next_m.start() if next_m else len(full_text), start + 600)
        caption_body = full_text[start:end].strip()
        caption_body = re.sub(r"\s+", " ", caption_body)
        if label not in captions and len(caption_body) > 20:
            prefix = m.group(0).rstrip()
            captions[label] = f"{prefix} {caption_body}"

    return captions


def max_figure_number(captions: dict[str, str]) -> int:
    """Return the highest numeric figure index found."""
    nums = []
    for label in captions:
        m = re.match(r"^(\d+)", label)
        if m:
            nums.append(int(m.group(1)))
    return max(nums) if nums else 0


def find_figure_label_on_page(page, img_rect, captions: dict[str, str]) -> str | None:
    """
    Search text blocks on this page near the image for a Figure N label.
    Prefers the caption CLOSEST below the image bottom edge (smallest non-negative
    distance from img_rect.y1 to the block top).  Captions above the image are
    penalised so they are only used when nothing below is found.
    Returns the matching label string (e.g. "1", "2") or None.
    """
    blocks = page.get_text("blocks")
    search_rect_y0 = img_rect.y0 - 200
    search_rect_y1 = img_rect.y1 + 200

    candidates: list[tuple[float, str]] = []
    for b in blocks:
        if b[6] != 0:
            continue  # not a text block
        if b[3] < search_rect_y0 or b[1] > search_rect_y1:
            continue  # outside the ±200 px window
        for m in FIGURE_LABEL_RE.finditer(b[4]):
            label = m.group(1)
            if label not in captions:
                continue
            dist_below = b[1] - img_rect.y1   # positive when block is below image
            dist_above = img_rect.y0 - b[3]   # positive when block is above image
            if dist_below >= 0:
                score = dist_below             # prefer closest below
            else:
                score = 10000 + max(dist_above, 0)  # penalise above-image captions
            candidates.append((score, label))

    if candidates:
        return min(candidates, key=lambda x: x[0])[1]

    # Broader fallback: search the full page text (first match)
    page_text = page.get_text("text")
    for m in FIGURE_LABEL_RE.finditer(page_text):
        label = m.group(1)
        if label in captions:
            return label

    return None


def union_rect(rects):
    """Return the bounding rect that covers all rects in the list."""
    import fitz
    x0 = min(r.x0 for r in rects)
    y0 = min(r.y0 for r in rects)
    x1 = max(r.x1 for r in rects)
    y1 = max(r.y1 for r in rects)
    return fitz.Rect(x0, y0, x1, y1)


def trim_crop_by_text(page, page_rect, crop, padding, image_rects=None):
    """
    When the crop covers most of the page (common in older PDFs where figures
    are embedded as full-page rasters), shrink the crop to exclude body text
    blocks (headers, footers, and paragraph columns).

    image_rects: list of fitz.Rect for the individual raster images on this
    page (sub-panels of the figure).  When provided and no single image
    dominates the page area, a text block is only trimmed if it lies entirely
    OUTSIDE every image rect — this prevents inter-panel captions/labels from
    causing incorrect edge trimming.

    Body text = text blocks with ≥4 alpha words AND >50 chars total.
    Trimming is directional: right-half text trims the right edge, etc.
    """
    import fitz

    page_area = page_rect.width * page_rect.height
    crop_area = crop.width * crop.height
    if crop_area / page_area < 0.65:
        return crop  # figure does not dominate the page — no trimming needed

    # Decide whether we are in "multi-panel" mode.
    # Multi-panel: multiple sub-panels, and none individually covers >50% of page.
    multi_panel = False
    if image_rects and len(image_rects) > 1:
        max_img_frac = max(
            (r.width * r.height) / page_area for r in image_rects
        )
        if max_img_frac < 0.50:
            multi_panel = True

    blocks = page.get_text("blocks")

    CAPTION_RE = re.compile(r"^\s*(?:Figure|FIGURE|Fig\.?)\s+\d")

    def is_body_text(text):
        """True for prose/headers, false for axis labels / figure annotations."""
        if CAPTION_RE.match(text):
            return False
        alpha_words = [w for w in text.split() if sum(c.isalpha() for c in w) >= 2]
        return len(alpha_words) >= 4 and len(text) > 50

    def inside_any_image(bx0, by0, bx1, by1):
        """True if this text block overlaps any of the individual image rects."""
        for r in (image_rects or []):
            if bx0 < r.x1 and bx1 > r.x0 and by0 < r.y1 and by1 > r.y0:
                return True
        return False

    body_blocks = [
        (b[0], b[1], b[2], b[3])
        for b in blocks
        if b[6] == 0 and is_body_text(b[4].strip())
    ]

    if not body_blocks:
        return crop

    new_x0, new_y0, new_x1, new_y1 = crop.x0, crop.y0, crop.x1, crop.y1
    cx = (crop.x0 + crop.x1) / 2
    cy = (crop.y0 + crop.y1) / 2

    for bx0, by0, bx1, by1 in body_blocks:
        # Skip blocks that don't overlap with the crop
        if bx1 <= crop.x0 or bx0 >= crop.x1 or by1 <= crop.y0 or by0 >= crop.y1:
            continue
        # In multi-panel mode, skip blocks that sit inside an image rect
        # (inter-panel text / scale bars / labels embedded in the figure area).
        if multi_panel and inside_any_image(bx0, by0, bx1, by1):
            continue
        # Choose ONE primary direction per block (mutually exclusive):
        #   right-column blocks ONLY trim the right edge;
        #   remaining blocks trim top or bottom based on position.
        if bx0 > cx:
            new_x1 = min(new_x1, bx0 - padding)
        elif by0 > cy:
            new_y1 = min(new_y1, by0 - padding)
        elif by1 < cy:
            new_y0 = max(new_y0, by1 + padding)

    # Safety: don't collapse the crop below a sensible minimum
    if new_x1 - new_x0 < 200 or new_y1 - new_y0 < 200:
        return crop

    return fitz.Rect(new_x0, new_y0, new_x1, new_y1)


def extract(paper_id: str, dpi: int, padding: int, output_dir: Path) -> None:
    try:
        import fitz
    except ImportError:
        print("ERROR: PyMuPDF not installed. Run: pip install pymupdf")
        sys.exit(1)

    pdf_path = PDFS_DIR / f"{paper_id}.pdf"
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        sys.exit(1)

    paper_dir = output_dir / paper_id
    paper_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    # ── Step 1: extract all figure captions from full PDF text ────────
    captions = extract_all_captions(doc)
    max_fig = max_figure_number(captions)

    print(f"Captions found: {sorted(captions.keys())}")
    print(f"Expected figures (max N): {max_fig}")
    print()

    # ── Step 2: collect all image rects, grouped by figure label ──────
    # label_rects: label -> list of (page_num, page, rect)
    label_rects: dict[str, list] = {}
    # unlabeled entries (in document order): list of (page_num, page, rect)
    unlabeled_rects: list = []

    seen_xrefs: set[int] = set()

    for page_num in range(len(doc)):
        page = doc[page_num]

        for img_info in page.get_images(full=True):
            xref = img_info[0]
            if xref in seen_xrefs:
                continue

            base_w, base_h = img_info[2], img_info[3]
            if base_w < 150 or base_h < 150:
                seen_xrefs.add(xref)
                continue

            try:
                rects = page.get_image_rects(xref)
            except Exception:
                rects = []
            if not rects:
                seen_xrefs.add(xref)
                continue

            seen_xrefs.add(xref)
            img_rect = rects[0]

            label = find_figure_label_on_page(page, img_rect, captions)

            if label:
                label_rects.setdefault(label, []).append((page_num, page, img_rect))
                print(f"  page {page_num+1:3d}  xref={xref}  label={label}")
            else:
                unlabeled_rects.append((page_num, page, img_rect))
                print(f"  page {page_num+1:3d}  xref={xref}  label=None (unlabeled)")

    # ── Step 3: assign unlabeled rects to missing figure numbers ──────
    # Group unlabeled rects by page — rects on the same page likely belong
    # to the same multi-panel figure.
    unlabeled_by_page: dict[int, list] = {}
    for page_num, page, img_rect in unlabeled_rects:
        unlabeled_by_page.setdefault(page_num, []).append((page_num, page, img_rect))

    # Sorted list of unlabeled page groups in document order
    unlabeled_groups = [unlabeled_by_page[k] for k in sorted(unlabeled_by_page)]

    expected = [str(n) for n in range(1, max_fig + 1)]
    missing = [n for n in expected if n not in label_rects]

    # One page-group of unlabeled rects per missing figure (document order)
    for fig_num, group in zip(missing, unlabeled_groups):
        label_rects[fig_num] = group
        pages_in_group = set(pn+1 for pn, _, _ in group)
        print(f"  [assigned {len(group)} unlabeled rect(s) on page(s) {pages_in_group}] -> label={fig_num}")

    # Any remaining page groups beyond what's needed are discarded
    extra_groups = unlabeled_groups[len(missing):]
    for group in extra_groups:
        for page_num, page, img_rect in group:
            print(f"  [discarded unlabeled on page {page_num+1}] (exceeds max_figure_number={max_fig})")

    images_saved = []

    # ── Step 3b: page-render fallback for still-missing figures ───────
    # For figures whose label appears in captions but no raster image was found
    # (vector-drawn figures), render the whole page and crop from just below the
    # nearest preceding body-text block down to just above the caption.
    CAPTION_RE_SIMPLE = re.compile(r"^\s*(?:Figure|FIGURE|Fig\.?)\s+\d")

    def is_body_text_block(text):
        alpha_words = [w for w in text.split() if sum(c.isalpha() for c in w) >= 2]
        return len(alpha_words) >= 4 and len(text) > 50 and not CAPTION_RE_SIMPLE.match(text)

    still_missing = [n for n in expected if n not in label_rects]
    if still_missing:
        print(f"\n  [fallback] labels still missing after raster pass: {still_missing}")

    for fig_num in still_missing:
        caption_text = captions.get(fig_num, "")
        found = False
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("blocks")
            # Find the caption block for this label on this page
            cap_block = None
            for b in blocks:
                if b[6] != 0:
                    continue
                for m in FIGURE_LABEL_RE.finditer(b[4]):
                    if m.group(1) == fig_num:
                        cap_block = b
                        break
                if cap_block:
                    break
            if not cap_block:
                continue

            cap_y = cap_block[1]   # top of caption block

            # Find the bottom edge of the nearest content block above cap_y.
            # Consider both body-text blocks AND figure caption blocks — the latter
            # handles the case where two figures share the same page (e.g. figs 7 & 8
            # on page 33): Figure 8's crop must start below Figure 7's caption.
            content_bottoms = [
                b[3] for b in blocks
                if b[6] == 0
                and b[3] < cap_y - 20
                and (is_body_text_block(b[4].strip()) or CAPTION_RE_SIMPLE.match(b[4].strip()))
            ]
            fig_top = max(content_bottoms) if content_bottoms else page.rect.y0

            page_rect = page.rect
            crop = fitz.Rect(
                page_rect.x0 + padding,
                max(page_rect.y0, fig_top),
                page_rect.x1 - padding,
                max(page_rect.y0, cap_y - padding),
            )

            # Skip degenerate crops
            if crop.height < 50 or crop.width < 100:
                continue

            pix = page.get_pixmap(matrix=mat, clip=crop, colorspace=fitz.csRGB)

            m_label = re.match(r'^(\d+)([a-zA-Z]*)$', fig_num)
            if m_label:
                fig_name = f"fig_{int(m_label.group(1)):03d}{m_label.group(2)}"
            else:
                fig_name = f"fig_{fig_num}"
            filename = f"{fig_name}.png"
            out_path = paper_dir / filename
            pix.save(str(out_path))

            cap_preview = (caption_text[:80] + "...") if len(caption_text) > 80 else caption_text
            print(
                f"  page {page_num+1:3d}  {filename}  {pix.width}x{pix.height}px"
                f"  label={fig_num}  [page-render fallback]  caption={cap_preview!r}"
            )

            entry = {
                "figure_label": fig_num,
                "filename": filename,
                "path": f"images/{paper_id}/{filename}",
                "page": page_num + 1,
                "width_px": pix.width,
                "height_px": pix.height,
                "caption": caption_text,
                "extraction_method": "page_render",
            }
            images_saved.append(entry)
            # Mark as found so Step 4 doesn't try to process it
            label_rects[fig_num] = []
            found = True
            break

        if not found:
            print(f"  [fallback] label={fig_num} — caption found nowhere on any page, skipping")

    # ── Step 4: render one combined crop per figure ────────────────────

    for label in sorted(label_rects.keys(), key=lambda x: int(re.match(r"\d+", x).group()) if re.match(r"\d+", x) else 999):
        entries = label_rects[label]
        if not entries:
            continue  # already handled by page-render fallback

        # All rects must be on the same page for a union crop to make sense.
        # Group by page and take the page with the most sub-panels.
        by_page: dict[int, list] = {}
        for page_num, page, img_rect in entries:
            by_page.setdefault(page_num, []).append((page, img_rect))

        best_page_num = max(by_page, key=lambda k: len(by_page[k]))
        page_entries = by_page[best_page_num]
        page = page_entries[0][0]
        rects = [r for _, r in page_entries]
        page_rect = page.rect

        combined = union_rect(rects)

        # Reject banner/header crops: wide and short (e.g. journal logos, GFZ header).
        # Check the on-page union rect — individual sub-images may be square but their
        # combined footprint is a wide horizontal strip.
        if combined.width > 0 and combined.width / combined.height > 4:
            print(f"  [skipped label={label}] union rect is banner-shaped ({combined.width:.0f}x{combined.height:.0f})")
            continue

        pad = padding
        crop = fitz.Rect(
            max(page_rect.x0, combined.x0 - pad),
            max(page_rect.y0, combined.y0 - pad),
            min(page_rect.x1, combined.x1 + pad),
            min(page_rect.y1, combined.y1 + pad),
        )
        crop = trim_crop_by_text(page, page_rect, crop, pad, image_rects=rects)

        m_label = re.match(r'^(\d+)([a-zA-Z]*)$', label)
        if m_label:
            fig_name = f"fig_{int(m_label.group(1)):03d}{m_label.group(2)}"
        else:
            fig_name = f"fig_{label}"
        filename = f"{fig_name}.png"
        out_path = paper_dir / filename

        pix = page.get_pixmap(matrix=mat, clip=crop, colorspace=fitz.csRGB)
        pix.save(str(out_path))

        caption = captions.get(label)
        cap_preview = (caption[:80] + "...") if caption and len(caption) > 80 else caption

        n_panels = sum(len(v) for v in by_page.values())
        panel_note = f"  ({n_panels} sub-panels combined)" if n_panels > 1 else ""
        print(
            f"  page {best_page_num+1:3d}  {filename}  {pix.width}x{pix.height}px"
            f"  label={label}  caption={cap_preview!r}{panel_note}"
        )

        entry = {
            "figure_label": label,
            "filename": filename,
            "path": f"images/{paper_id}/{filename}",
            "page": best_page_num + 1,
            "width_px": pix.width,
            "height_px": pix.height,
            "caption": caption,
        }
        images_saved.append(entry)

    doc.close()

    # ── Step 5: write manifest ─────────────────────────────────────────
    manifest = {
        "paper_id": paper_id,
        "pdf_path": str(pdf_path),
        "dpi": dpi,
        "max_figure_number": max_fig,
        "captions": captions,
        "total_images_extracted": len(images_saved),
        "figures": images_saved,
    }
    manifest_path = paper_dir / "_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print()
    print(f"paper_id:           {paper_id}")
    print(f"max_figure_number:  {max_fig}  (aim to keep this many figures)")
    print(f"images_extracted:   {len(images_saved)}")
    print(f"output_dir:         {paper_dir}")
    print(f"manifest:           {manifest_path}")


def main():
    parser = argparse.ArgumentParser(description="Crop figure regions from a PDF")
    parser.add_argument("paper_id")
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--padding", type=int, default=12)
    parser.add_argument("--output-dir", metavar="DIR", default=str(IMAGES_DIR))
    args = parser.parse_args()
    extract(args.paper_id, args.dpi, args.padding, Path(args.output_dir))


if __name__ == "__main__":
    main()
