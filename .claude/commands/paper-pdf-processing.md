# paper-pdf-processing

Process a paper's PDF: extract text, extract figures, validate/update the JSON metadata, and register the PDF in `pdf_validation.json`.

## Input

A paper ID (e.g. `becerra_2013_arauco_basin_seismic_tecto`). If no argument is given, find papers where a PDF exists in `pdfs/` but either:
- `pdf_text/{id}.txt` is missing, OR
- `images/{id}/figures.json` is missing, OR
- the entry in `pdf_validation.json` has `"validated": false`

Process the first such paper found.

## Step 1 — Verify the PDF exists

Check `pdfs/{paper_id}.pdf`. If it doesn't exist, print an error and stop.

## Step 2 — Extract text (if not already done)

Check if `pdf_text/{paper_id}.txt` exists. If not, run:

```bash
python extract_pdf_text.py {paper_id} > _tmp_extract.txt 2>&1
```

Read `_tmp_extract.txt` to confirm success, then delete it.

## Step 3 — Extract figures (if not already done)

Check if `images/{paper_id}/figures.json` exists. If not, invoke the `figure-extractor` command for this paper ID.

## Step 4 — Validate and update JSON metadata

Use the `/pdf-validator` skill to validate `papers/{paper_id}.json` against the PDF. This will:
- Verify bibliographic fields (title, authors, year, DOI)
- Extract/update acquisition parameters
- Find data availability links
- Update `analysis_confidence` and `analysis_notes`

## Step 5 — Extract resolution and new fields

Run the two extraction scripts on this paper:

```bash
python extract_resolution.py {paper_id} > _tmp_res.txt 2>&1
python extract_fields.py {paper_id} > _tmp_fields.txt 2>&1
```

Read and report the outputs, then delete the temp files.

## Step 6 — Register in pdf_validation.json

Add or update the entry in `pdf_validation.json`:

```json
{
  "id": "{paper_id}",
  "pdf_file": "pdfs/{paper_id}.pdf",
  "validated": true,
  "validated_at": "YYYY-MM-DD",
  "notes": "Processed via paper-pdf-processing command. {brief summary of changes}"
}
```

If the entry already exists, update it in place.

## Step 7 — Report

Print a concise summary:
- Paper ID and title
- Text extraction: pages extracted, file size
- Figures: count extracted
- JSON fields updated (list each change)
- Resolution fields found
- New fields populated (tectonic_setting, earthquakes, migration_type, etc.)
