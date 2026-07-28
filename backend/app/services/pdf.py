"""PDF text extraction via pypdf."""

from __future__ import annotations

import io

from pypdf import PdfReader


class PdfExtractionError(Exception):
    pass


def extract_text_from_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # pypdf raises a variety of exceptions
        raise PdfExtractionError(f"Could not read PDF: {exc}") from exc
    text = "\n".join(pages).strip()
    if not text:
        raise PdfExtractionError(
            "No extractable text found in PDF (it may be a scanned image)."
        )
    return text
