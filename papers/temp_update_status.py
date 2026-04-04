import json
import sys

filepath = "C:/Users/mauri/Documents/projects/chilean-seismic-marine-lines/papers/survey_results.json"

with open(filepath, 'r', encoding='utf-8') as f:
    data = json.load(f)

papers = data.get('papers', [])
count_before = sum(1 for p in papers if p.get('status') == 'TO_ANALYZE')
print(f"Papers with TO_ANALYZE before: {count_before}")

for paper in papers:
    if paper.get('status') == 'TO_ANALYZE':
        paper['status'] = 'ANALYZED'

count_after = sum(1 for p in papers if p.get('status') == 'TO_ANALYZE')
count_analyzed = sum(1 for p in papers if p.get('status') == 'ANALYZED')
print(f"Papers with TO_ANALYZE after: {count_after}")
print(f"Papers with ANALYZED after: {count_analyzed}")

with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("survey_results.json updated successfully.")
