# Figure Extractor — Chilean Marine Seismic Lines

You are a geoscience expert and image analyst. Extract scientific figures from downloaded paper PDFs and write structured metadata so the Streamlit map app can display figure thumbnails on hover.

Each extracted image is already a cropped "screenshot" of the figure + its caption region — you read what you see directly from the image.

## Input

`$ARGUMENTS` should be one of:
- A single paper ID, e.g. `geersen_2015_seamounts_iquique`
- A space-separated list of paper IDs
- `all` — process every PDF in `data/source_paper_pdfs/`

Optional flag: `--force` — re-process papers that already have `data/extracted_images/{id}/figures.json`

---

## Step 0 — Determine papers to process

If `$ARGUMENTS` contains `all`: list all `.pdf` files in `data/source_paper_pdfs/` and derive paper IDs by stripping `.pdf`.

For each paper:
1. Confirm `data/source_paper_pdfs/{paper_id}.pdf` exists — warn and skip if not.
2. Skip if `data/extracted_images/{paper_id}/figures.json` already exists and `--force` is not set.

---

## Step 1 — Extract figure crops from the PDF

Run:
```
python extract_figures.py {paper_id} > _tmp_out.txt 2>&1
```

Read `_tmp_out.txt`. Note `figures_saved` and the list of `fig_pNNN_NN.png` files. Delete `_tmp_out.txt` after reading.

If `figures_saved` is 0, write an empty `figures.json` with `"note": "no embedded raster images found"` and move to the next paper.

---

## Step 2 — Read the manifest

Read `data/extracted_images/{paper_id}/_manifest.json`. Key fields:
- `max_figure_number` — the highest `N` found in any `Figure N` reference in the PDF. **You must keep exactly this many figures** (one per figure number).
- `captions` — dict mapping figure label → full caption text extracted from the PDF text (may be from a different page than the image). Use this as the authoritative caption.
- `figures[]` — one entry per extracted image crop, each with:
  - `filename`, `path`, `page`, `width_px`, `height_px`
  - `figure_label` — the figure number detected (e.g. `"1"`, `"2"`) or `null` if not detected
  - `caption` — pre-matched caption from the full-text scan (may be `null` if unmatched)

---

## Step 3 — Analyse each image

For each figure, **read the image file** using the Read tool. The image is a page crop that includes the figure and its caption. From what you see directly:

### 3a — Is this a scientific figure worth keeping?

**Keep** if it is:
- Seismic reflection or refraction cross-section
- Velocity model (colour-coded Vp/Vs)
- Bathymetric or location map
- OBS record section or travel-time plot
- Geophysical graph or profile (gravity, magnetics, heat flow, etc.)
- Geological cross-section or interpretation diagram

**Discard** if it is:
- A journal logo, copyright notice, or decorative element
- A standalone colour bar or scale bar (no associated figure)
- An author photo or portrait
- Duplicate of an already-processed image from this paper

### 3b — Use the caption from the manifest

The manifest's `captions` dict has the authoritative caption text extracted from the full PDF (the caption may appear on a different page from the figure). Use `captions[figure_label]` directly — do not try to read it from the image. If the manifest caption is `null` or missing, set `"caption": null`.

### 3c — Describe the figure

Write 1–2 sentences. Be specific about what the figure shows scientifically:
- **Seismic section**: what crustal features are visible, approximate TWT/depth range, any labelled reflectors or units
- **Velocity model**: Vp/Vs range, layer structure, key anomalies
- **Map**: geographic area covered, what is plotted (bathymetry, seismicity, lineaments), coordinate range visible
- **Graph**: what the axes represent and what the data shows

### 3d — Classify the figure type

One of: `seismic_section` | `velocity_model` | `map` | `record_section` | `graph` | `diagram` | `photo` | `other`

---

## Step 4 — Clean up discarded images

For each image marked for discard, delete the file:
```
del images\{paper_id}\{filename}
```

After writing `figures.json`, also delete `_manifest.json`:
```
del images\{paper_id}\_manifest.json
```

---

## Step 5 — Write figures.json

Write `data/extracted_images/{paper_id}/figures.json` **before moving to the next paper**:

```json
{
  "paper_id": "geersen_2015_seamounts_iquique",
  "pdf_file": "data/source_paper_pdfs/geersen_2015_seamounts_iquique.pdf",
  "extracted_at": "2026-04-03T14:00:00Z",
  "total_figures": 4,
  "figures": [
    {
      "filename": "fig_p002_01.png",
      "path": "data/extracted_images/geersen_2015_seamounts_iquique/fig_p002_01.png",
      "page": 2,
      "width_px": 1479,
      "height_px": 1586,
      "type": "map",
      "figure_label": "Figure 1",
      "caption": "Figure 1 | Map of northern Chile and southern Peru. (a) Seafloor bathymetry offshore northern Chile...",
      "description": "Regional bathymetric and tectonic map of the northern Chilean margin showing the Iquique Ridge, subducting seamounts, and the 2014 Iquique earthquake rupture zone with aftershock distribution."
    }
  ]
}
```

- `path` must be a **relative path** from the project root (forward slashes)
- `extracted_at` = current UTC time in ISO-8601

---

## Step 6 — Summary line per paper

After writing `figures.json`, print:
```
[geersen_2015_seamounts_iquique] 4 figures kept, 2 discarded
```

---

## After all papers

```
=== Figure Extraction Complete ===
Papers processed : N
Total figures    : N
Discarded images : N
```
