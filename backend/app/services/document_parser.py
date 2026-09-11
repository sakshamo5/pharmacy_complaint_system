"""
Document Parser Service
Extracts raw text from uploaded files.
Supports: PDF, DOCX, TXT, EML (email)
Production-grade OCR is NOT required per spec — we extract digital text only.
"""
import email
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_document(file_bytes: bytes, filename: str) -> str:
    """
    Dispatch to the correct parser based on file extension.
    Returns a single string of extracted text.
    Raises ValueError for unsupported formats.
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        return _parse_pdf(file_bytes)
    elif ext == ".docx":
        return _parse_docx(file_bytes)
    elif ext == ".txt":
        return _parse_txt(file_bytes)
    elif ext in (".eml", ".email"):
        return _parse_eml(file_bytes)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Allowed: PDF, DOCX, TXT, EML")


def _parse_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pdfplumber (handles multi-page, tables)."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages_text = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    pages_text.append(f"[Page {i + 1}]\n{text}")
            return "\n\n".join(pages_text)
    except ImportError:
        raise RuntimeError("pdfplumber not installed. Run: pip install pdfplumber")
    except Exception as e:
        logger.error(f"PDF parsing error: {e}")
        raise ValueError(f"Could not parse PDF: {str(e)}")


def _parse_docx(file_bytes: bytes) -> str:
    """Extract text from Word document using python-docx."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        # Also extract from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)
        return "\n".join(paragraphs)
    except ImportError:
        raise RuntimeError("python-docx not installed. Run: pip install python-docx")
    except Exception as e:
        logger.error(f"DOCX parsing error: {e}")
        raise ValueError(f"Could not parse DOCX: {str(e)}")


def _parse_txt(file_bytes: bytes) -> str:
    """Decode plain text — try UTF-8 then fall back to latin-1."""
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")


def _parse_eml(file_bytes: bytes) -> str:
    """
    Parse .eml email files using Python stdlib.
    Extracts Subject, From, Date, and all text/plain body parts.
    """
    msg = email.message_from_bytes(file_bytes)

    parts = []
    # Email headers relevant to complaint context
    for header in ["Subject", "From", "To", "Date"]:
        value = msg.get(header)
        if value:
            parts.append(f"{header}: {value}")

    parts.append("")  # blank line before body

    # Walk multipart messages to find text/plain payloads
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    try:
                        charset = part.get_content_charset() or "utf-8"
                        parts.append(payload.decode(charset))
                    except Exception:
                        parts.append(payload.decode("latin-1"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            try:
                parts.append(payload.decode(charset))
            except Exception:
                parts.append(payload.decode("latin-1"))

    return "\n".join(parts)
