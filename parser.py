import io
from typing import Tuple
from PyPDF2 import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    texts = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        texts.append(page_text)
    return "\n".join(texts)


def clean_text(text: str) -> str:
    lines = [l.strip() for l in text.splitlines()]
    lines = [l for l in lines if l]
    return "\n".join(lines)


def parse_pdf_resume(file_bytes: bytes) -> Tuple[str, str]:
    raw = extract_text_from_pdf(file_bytes)
    cleaned = clean_text(raw)
    return raw, cleaned
