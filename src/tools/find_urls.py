import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent.parent
PAPERS_DIR = ROOT / "papers"
EXCLUDE = {"survey_results.json", "data_availability.json", "schema.json"}

url_map = defaultdict(list)  # url -> [paper_id, ...]

for path in sorted(PAPERS_DIR.glob("*.json")):
    if path.name in EXCLUDE:
        continue
    data = json.loads(path.read_text(encoding="utf-8"))
    for entry in data.get("data", []):
        url = entry.get("url")
        if url:
            url_map[url].append(data["id"])

with open(ROOT / "_urls.txt", "w", encoding="utf-8") as f:
    for url, papers in sorted(url_map.items()):
        f.write(f"{url}\n    papers: {', '.join(papers[:3])}{'...' if len(papers)>3 else ''}\n")

print(f"Found {len(url_map)} unique URLs")
