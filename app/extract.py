import re
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

try:
    import docx  # type: ignore[import-not-found]
except Exception:  # keep import optional for IDEs
    docx = None  # type: ignore[assignment]

try:
    import pytesseract  # type: ignore[import-not-found]
except Exception:
    pytesseract = None  # type: ignore[assignment]

try:
    from pdf2image import convert_from_path  # type: ignore[import-not-found]
except Exception:
    convert_from_path = None  # type: ignore[assignment]

try:
    from pypdf import PdfReader  # type: ignore[import-not-found]
except Exception:
    PdfReader = None  # type: ignore[assignment]

try:
    from PIL import Image  # type: ignore[import-not-found]
except Exception:
    Image = None  # type: ignore[assignment]

from .db import insert_extracted_field, log_audit


_tess_cmd = os.getenv("TESSERACT_CMD")
if _tess_cmd and pytesseract is not None:
    # Configure pytesseract to use the specified Tesseract binary (Windows-friendly)
    pytesseract.pytesseract.tesseract_cmd = _tess_cmd

def extract_text_from_pdf(path: Path) -> str:
    # Preferred path: OCR via pdf2image + Tesseract for scanned PDFs
    if convert_from_path is not None and pytesseract is not None:
        images = convert_from_path(str(path))
        text_parts: List[str] = []
        for img in images:
            text_parts.append(pytesseract.image_to_string(img))
        return "\n".join(text_parts)

    # Fallback: direct text extraction from embedded PDF text
    if PdfReader is not None:
        try:
            reader = PdfReader(str(path))
            parts: List[str] = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
            return "\n".join(parts)
        except Exception:
            pass

    # If we reach here, provide actionable guidance
    if convert_from_path is None:
        raise RuntimeError("pdf2image not installed. Install with: pip install pdf2image (and Poppler on Windows)")
    if pytesseract is None:
        raise RuntimeError("pytesseract not installed. Install with: pip install pytesseract and Tesseract OCR")
    return ""


def extract_text_from_image(path: Path) -> str:
    if Image is None:
        raise RuntimeError("Pillow not installed. Install with: pip install Pillow")
    if pytesseract is None:
        raise RuntimeError("pytesseract not installed. Install with: pip install pytesseract and Tesseract OCR")
    img = Image.open(path)
    return pytesseract.image_to_string(img)


def extract_text_from_docx(path: Path) -> str:
    if docx is None:
        # Gracefully degrade: skip DOCX extraction if dependency missing
        return ""
    d = docx.Document(str(path))
    return "\n".join(p.text for p in d.paragraphs)


def extract_text_from_txt(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    if ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        return extract_text_from_image(path)
    if ext == ".docx":
        return extract_text_from_docx(path)
    if ext == ".txt":
        return extract_text_from_txt(path)
    return ""


POLICY_NUMBER_RE = re.compile(r"(?:policy|policy number)[:\s]*([A-Z0-9-]{6,})", re.I)
CLAIM_NUMBER_RE = re.compile(r"(?:claim|claim number)[:\s]*([A-Z0-9-]{6,})", re.I)
ICD10_RE = re.compile(r"\b([A-TV-Z][0-9][0-9A-Z](?:\.[0-9A-Z]{1,4})?)\b")


def extract_structured_fields(claim_id: int, document_id: int, text: str) -> None:
    candidates: List[Tuple[str, str, Optional[float]]] = []
    if m := POLICY_NUMBER_RE.search(text):
        candidates.append(("policy_number", m.group(1), 0.9))
    if m := CLAIM_NUMBER_RE.search(text):
        candidates.append(("claim_number", m.group(1), 0.9))
    for code in set(ICD10_RE.findall(text)):
        candidates.append(("icd10_code", code, 0.8))

    for field_name, field_value, confidence in candidates:
        insert_extracted_field(
            claim_id=claim_id,
            document_id=document_id,
            field_name=field_name,
            field_value=field_value,
            confidence=confidence,
        )

    log_audit("fields_extracted", f"extracted {len(candidates)} fields", claim_id=claim_id, document_id=document_id)


