from pathlib import Path
from typing import Dict, List

import fitz


def extract_text_from_pdf(pdf_path: Path) -> List[Dict[str, object]]:
    text_by_page = []
    with fitz.open(pdf_path) as doc:
        for page_number, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            text_by_page.append({"page": page_number, "text": text})
    return text_by_page
