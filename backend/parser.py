import io
from typing import Tuple
from PyPDF2 import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    从 PDF 字节流中提取所有页面文本
    """
    pdf = PdfReader(io.BytesIO(file_bytes))
    texts = []
    for page in pdf.pages:
        page_text = page.extract_text() or ""
        texts.append(page_text)
    return "\n".join(texts)


def clean_text(text: str) -> str:
    """
    对文本做简单清洗：
    - 去掉多余空白
    - 去掉重复空行
    """
    lines = [line.strip() for line in text.splitlines()]
    # 去掉完全空的行
    lines = [line for line in lines if line]
    cleaned = "\n".join(lines)
    return cleaned


def parse_pdf_resume(file_bytes: bytes) -> Tuple[str, str]:
    """
    返回 (raw_text, cleaned_text)
    """
    raw_text = extract_text_from_pdf(file_bytes)
    cleaned = clean_text(raw_text)
    return raw_text, cleaned
