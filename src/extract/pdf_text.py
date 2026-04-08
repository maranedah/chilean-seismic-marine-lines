"""Extract full text from a PDF and save to pdf_text/{paper_id}.txt

Usage:
    python -m src.extract.pdf_text paper_id1 paper_id2 ...
"""
import argparse
import os
import sys
import fitz  # PyMuPDF
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


def extract(paper_id: str) -> None:
    pdf_path = str(ROOT / 'data' / 'source_paper_pdfs' / f'{paper_id}.pdf')
    out_path = str(ROOT / 'data' / 'extracted_text' / f'{paper_id}.txt')

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


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(description='Extract full text from paper PDFs')
    parser.add_argument('paper_ids', nargs='+', metavar='PAPER_ID',
                        help='One or more paper IDs to extract')
    args = parser.parse_args()

    for pid in args.paper_ids:
        extract(pid)


if __name__ == '__main__':
    main()
