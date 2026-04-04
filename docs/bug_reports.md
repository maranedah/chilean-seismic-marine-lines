# Figure Extractor — Bug Reports

---

## BUG-001: Journal/institutional header images falsely assigned as figures

**Severity:** High  
**Affects:** `maksymowicz_2015_wedge_geometry_tecto` (fig_005), `storch_2021_iquique_seismic_images` (fig_003), `tilmann_2008_outer_rise_epsl` (fig_002)

**Symptom:**  
Page 1 of some PDFs contains a journal banner or institutional logo embedded as a raster image (e.g. the Elsevier/Tectonophysics header, the GFZ Helmholtz-Zentrum Potsdam logo). These images are wide and short (~1593×329 px) and pass the 150 px minimum-size filter. When no figure label is detected on page 1, the script assigns the image to the next missing figure number via the unlabeled→missing logic.

**Root cause:**  
No aspect-ratio guard. Banner images typically have width/height > 4. The current filter only rejects images smaller than 150×150 px.

**Fixed:**  
Added a union-rect aspect ratio guard in the render loop: if `combined.width / combined.height > 4`, the figure is skipped with a log message. This catches both single wide images and multi-image header groups (like GFZ's two-part logo) whose individual base sizes are not obviously banner-shaped but whose combined on-page footprint is. Deleted false-positive files.

---

## BUG-002: Zero captions extracted — Spanish or non-standard caption format

**Severity:** High  
**Affects:** `moscoso_contreras-reyes_2012_outer_rise_andean_geo`, `vargas-cordero_2016_gas_hydrate_chiloe`

**Symptom:**  
`FIGURE_LABEL_RE` matched zero captions → `max_figure_number=0` → all embedded images discarded, despite 6–7 raster images being present in each PDF.

**Root cause:**  
The regex only matches English prefixes (`Figure`, `FIGURE`, `Fig.`). Andean Geology papers may use Spanish `Figura`/`FIGURA`, or the PDFs may lack a searchable text layer (scanned without OCR).

**Suggested fix:**  
1. Extend `FIGURE_LABEL_RE` to also match `Figura`, `FIGURA`.
2. Add a fallback: if no captions are found and the page text is empty, flag as "scanned PDF — manual extraction required".

**Workaround applied:**  
`figures.json` written with `total_figures: 0` and a note.

---

## BUG-003: Vector-graphic figures not extracted

**Severity:** Medium  
**Affects:** `ramos_2018_tipteq_reflection_tecto` (6/11 missing), `storch_2021_iquique_seismic_images` (2/8 missing), `tilmann_2008_outer_rise_epsl` (7/10 missing)

**Symptom:**  
`max_figure_number` is correctly detected but many figures are missing because they are rendered as PDF vector objects rather than embedded raster images. `page.get_images()` only returns embedded rasters.

**Suggested fix:**  
For pages where a figure label is known to exist (from caption scan) but `get_images()` returns nothing substantial, fall back to rendering the full page as a pixmap and crop using the detected text block positions.

**Workaround applied:**  
`figures.json` written with available figures only; a `note` field documents missing figures.

---

## BUG-004: Non-standard filename for sub-labelled figures (3a, 3b)

**Severity:** Low  
**Affects:** `von_huene_ranero_2003_antofagasta_erosion_jgr` (produces `fig_3a.png`, `fig_3b.png`)

**Symptom:**  
When the detected figure label is `"3a"` or `"3b"`, the output filename lacks zero-padding on the numeric part, breaking sorted ordering.

**Root cause:**  
```python
fig_name = f"fig_{int(label):03d}" if label.isdigit() else f"fig_{label}"
```
Non-numeric labels fall into the `else` branch without zero-padding.

**Fixed:**  
```python
m_label = re.match(r'^(\d+)([a-zA-Z]*)$', label)
if m_label:
    fig_name = f"fig_{int(m_label.group(1)):03d}{m_label.group(2)}"
else:
    fig_name = f"fig_{label}"
```
Applied in `extract_figures.py`.

---

## BUG-005: Wrong PDF downloaded for diaz-naveas_1999

**Severity:** High  
**Affects:** `diaz-naveas_1999_sediment_subduction_Chile_GEOMAR`

**Symptom:**  
`pdfs/diaz-naveas_1999_sediment_subduction_Chile_GEOMAR.pdf` is a completely unrelated paper: *"Antiprotozoal, Antitubercular and Cytotoxic Potential of Cyanobacterial Extracts from Ireland"* (Natural Product Communications, 2011, 6 pages).

**Root cause:**  
The PDF downloader resolved the wrong URL for this paper ID.

**Fix:**  
Manually obtain the correct PDF (Diaz-Naveas 1999, GEOMAR report on sediment subduction along Chile) and replace the current file.
