from __future__ import annotations

from pathlib import Path


async def extract_text_from_file(file_path: str | Path) -> str | None:
    """从 PDF 或 DOCX 文件中提取纯文本。

    支持格式：.pdf、.docx、.txt
    如果文件格式不支持或解析失败则返回 None。
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf(path)
    elif suffix == ".docx":
        return _extract_docx(path)
    elif suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")
    else:
        return None


def _extract_pdf(path: Path) -> str | None:
    """使用 PyMuPDF 从 PDF 文件中提取文本。"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return None

    doc = fitz.open(path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text.strip() or None


def _extract_docx(path: Path) -> str | None:
    """使用 python-docx 从 DOCX 文件中提取文本（仅段落文本）。"""
    try:
        import docx
    except ImportError:
        return None

    doc = docx.Document(path)
    text = "\n".join(para.text for para in doc.paragraphs)
    return text.strip() or None
