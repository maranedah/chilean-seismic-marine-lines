import json
import os
import glob

papers_dir = "C:/Users/mauri/Documents/projects/chilean-seismic-marine-lines/papers"

paper_files = [f for f in glob.glob(os.path.join(papers_dir, "*.json"))
               if not os.path.basename(f) in ("survey_results.json", "data_availability.json")]

total = 0
open_access_count = 0
raw_count = 0
semi_processed_count = 0
processed_count = 0
papers_with_open_data = []

for filepath in paper_files:
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            p = json.load(f)
        except Exception as e:
            print(f"ERROR reading {filepath}: {e}")
            continue
    total += 1
    has_open = False
    for entry in p.get('data', []):
        cls = entry.get('classification', '').upper()
        if cls == 'RAW':
            raw_count += 1
        elif cls == 'SEMI_PROCESSED':
            semi_processed_count += 1
        elif cls == 'PROCESSED':
            processed_count += 1
        if entry.get('access') == 'open':
            has_open = True
    if has_open:
        open_access_count += 1
        papers_with_open_data.append(p.get('id', os.path.basename(filepath)))

print(f"Total papers analyzed: {total}")
print(f"Papers with at least one open-access dataset: {open_access_count}")
print(f"Dataset classification breakdown:")
print(f"  RAW: {raw_count}")
print(f"  SEMI_PROCESSED: {semi_processed_count}")
print(f"  PROCESSED: {processed_count}")
print(f"  TOTAL datasets: {raw_count + semi_processed_count + processed_count}")
print()
print("Papers with open data:")
for pid in sorted(papers_with_open_data):
    print(f"  - {pid}")
