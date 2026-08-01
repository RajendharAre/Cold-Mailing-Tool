"""Resume intake: extract plain text from uploaded files (PDF / Markdown / TXT)."""

from __future__ import annotations

from io import BytesIO


def extract_resume_text(filename: str, data: bytes) -> str:
    """Extract plain text from a resume file. PDF requires ``pypdf``."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return _extract_pdf_text(data)
    return _decode_text(data)


def _extract_pdf_text(data: bytes) -> str:
    pypdf = _load_pypdf()
    reader = pypdf.PdfReader(BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def _load_pypdf():
    try:
        import pypdf  # type: ignore

        return pypdf
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "pypdf is required to read PDF resumes. Install it with: pip install pypdf"
        ) from exc


def _decode_text(data: bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    try:
        return data.decode("utf-8").strip()
    except UnicodeDecodeError:
        return data.decode("latin-1").strip()
