# Test Reviewer — Chilean Marine Seismic Lines

You are a QA engineer. Your job is to verify that the project's core functionality works correctly by running targeted checks and reporting what passes, what fails, and what is untestable without a live environment.

## Environment note

This project runs on **Windows**. All commands that produce output must redirect to a temp file:
```bash
python some_script.py > _tmp_out.txt 2>&1
# Read the file, then delete it
```
Never assume output appeared in the terminal.

---

## What to test

If `$ARGUMENTS` is provided (e.g. `/test-reviewer download`), focus only on that area. Otherwise run all checks below.

---

## Step 1 — Validate paper JSON files

```bash
python -c "
import json, os, sys
papers_dir = 'data/extracted_jsons'
errors = []
required_fields = ['id', 'title', 'year', 'doi', 'location', 'data']
for fname in os.listdir(papers_dir):
    if not fname.endswith('.json') or fname == 'survey_results.json':
        continue
    path = os.path.join(papers_dir, fname)
    try:
        with open(path) as f:
            p = json.load(f)
        for field in required_fields:
            if field not in p:
                errors.append(f'{fname}: missing field \"{field}\"')
        loc = p.get('location', {})
        lat = loc.get('latitude')
        lon = loc.get('longitude')
        if lat is None or lon is None:
            errors.append(f'{fname}: missing lat/lon')
        elif not (-57 <= lat <= -18):
            errors.append(f'{fname}: latitude {lat} outside Chile range (-57 to -18)')
        elif not (-80 <= lon <= -65):
            errors.append(f'{fname}: longitude {lon} outside Chile range (-80 to -65)')
        for i, d in enumerate(p.get('data', [])):
            if d.get('access') not in ('open', 'restricted', 'embargoed', 'unknown'):
                errors.append(f'{fname} data[{i}]: invalid access value \"{d.get(\"access\")}\"')
    except json.JSONDecodeError as e:
        errors.append(f'{fname}: invalid JSON — {e}')
    except Exception as e:
        errors.append(f'{fname}: unexpected error — {e}')
if errors:
    print(f'FAIL — {len(errors)} error(s):')
    for e in errors: print(' ', e)
else:
    import glob
    count = len([f for f in os.listdir(papers_dir) if f.endswith('.json') and f != 'survey_results.json'])
    print(f'PASS — {count} paper JSON files valid')
" > _tmp_out.txt 2>&1
```

Read `_tmp_out.txt`, report results, delete it.

---

## Step 2 — Validate survey_results.json

```bash
python -c "
import json, os
with open('data/extracted_jsons/survey_results.json') as f:
    data = json.load(f)
papers = data if isinstance(data, list) else data.get('papers', [])
valid_statuses = {'TO_ANALYZE', 'ANALYZED', 'SKIPPED', 'ERROR'}
errors = []
for p in papers:
    if 'id' not in p:
        errors.append(f'Entry missing id: {p}')
    if p.get('status') not in valid_statuses:
        errors.append(f'{p.get(\"id\")}: invalid status \"{p.get(\"status\")}\"')
analyzed = [p for p in papers if p.get('status') == 'ANALYZED']
to_analyze = [p for p in papers if p.get('status') == 'TO_ANALYZE']
if errors:
    print(f'FAIL — {len(errors)} error(s):')
    for e in errors: print(' ', e)
else:
    print(f'PASS — {len(papers)} total | {len(analyzed)} ANALYZED | {len(to_analyze)} TO_ANALYZE')
" > _tmp_out.txt 2>&1
```

Read `_tmp_out.txt`, report results, delete it.

---

## Step 3 — Check JSON/paper ID consistency

```bash
python -c "
import json, os
results_path = 'data/extracted_jsons/survey_results.json'
with open(results_path) as f:
    data = json.load(f)
index = data if isinstance(data, list) else data.get('papers', [])
index_ids = {p['id'] for p in index if 'id' in p}
file_ids = {
    os.path.splitext(f)[0]
    for f in os.listdir('papers')
    if f.endswith('.json') and f != 'survey_results.json'
}
in_index_not_file = index_ids - file_ids
in_file_not_index = file_ids - index_ids
issues = []
if in_index_not_file:
    issues.append(f'In survey_results but no JSON file: {sorted(in_index_not_file)}')
if in_file_not_index:
    issues.append(f'JSON file exists but not in survey_results: {sorted(in_file_not_index)}')
if issues:
    print('FAIL:')
    for i in issues: print(' ', i)
else:
    print(f'PASS — {len(file_ids)} JSON files match {len(index_ids)} survey_results entries')
" > _tmp_out.txt 2>&1
```

Read `_tmp_out.txt`, report results, delete it.

---

## Step 4 — Syntax-check Python files

```bash
python -m py_compile app.py download.py && echo "PASS — no syntax errors" > _tmp_out.txt 2>&1 || echo "FAIL — syntax errors found" >> _tmp_out.txt 2>&1
```

Read `_tmp_out.txt`, report results, delete it.

---

## Step 5 — Dry-run the downloader

```bash
python download.py --report > _tmp_out.txt 2>&1
```

Read `_tmp_out.txt`. Verify:
- No Python tracebacks
- Output mentions open-access datasets (or clearly states there are none)
- Exit without error

Delete `_tmp_out.txt` after reading.

---

## Step 6 — Check open-access URLs reachable (spot check)

Read up to 3 paper JSON files that have `"access": "open"` with a non-null URL. For each, use WebFetch on the URL to confirm it returns a valid response (not 404 / 403 / timeout). Report which URLs are reachable and which are broken.

If no open-access URLs exist in the dataset, skip this step and note it.

---

## Step 7 — Print final report

```
## Test Review Report — YYYY-MM-DD

| Check | Result | Notes |
|-------|--------|-------|
| Paper JSON validation | PASS/FAIL | N files, N errors |
| survey_results.json | PASS/FAIL | N papers |
| ID consistency | PASS/FAIL | |
| Python syntax | PASS/FAIL | |
| Downloader dry-run | PASS/FAIL | |
| URL spot-check | PASS/FAIL/SKIPPED | N checked, N broken |

### Issues requiring attention
- [file or check] Description of problem and suggested fix

### All clear
- [check] What passed and why it matters
```

If everything passes, say so clearly. Do not invent failures.
