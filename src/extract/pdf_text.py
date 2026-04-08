"""Extract full text from a PDF and save to pdf_text/{paper_id}.txt"""
import sys
import os
import fitz  # PyMuPDF
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent.parent.parent

def extract(paper_id: str) -> None:
    pdf_path = str(ROOT / 'pdfs' / f'{paper_id}.pdf')
    out_path = str(ROOT / 'pdf_text' / f'{paper_id}.txt')

    if not os.path.exists(pdf_path):
        print(f'SKIP {paper_id}: PDF not found')
        return
    if os.path.exists(out_path):
        print(f'SKIP {paper_id}: already extracted')
        return

    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            pages.append(f'--- Page {i+1} ---\n{text}')
    full_text = '\n'.join(pages)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(full_text)
    print(f'OK {paper_id}: {doc.page_count} pages, {len(full_text)} chars -> {out_path}')

if __name__ == '__main__':
    ids = sys.argv[1:]
    if not ids:
        print('Usage: python -m src.extract.pdf_text paper_id1 paper_id2 ...')
        sys.exit(1)
    for pid in ids:
        extract(pid)
