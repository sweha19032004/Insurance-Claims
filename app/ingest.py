import os
from pathlib import Path
from typing import Iterable, List, Tuple

from .db import insert_document, log_audit


SUPPORTED_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".docx", ".txt"}


def discover_documents(folder: str) -> List[Path]:
    base = Path(folder)
    files: List[Path] = []
    for path in base.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS:
            files.append(path)
    return files


def register_documents(claim_id: int, files: Iterable[Path]) -> List[int]:
    document_ids: List[int] = []
    for f in files:
        file_type = f.suffix.lower().lstrip(".")
        doc_id = insert_document(claim_id, f.name, file_type, None)
        document_ids.append(doc_id)
        log_audit("document_registered", f"Registered {f.name}", claim_id=claim_id, document_id=doc_id)
    return document_ids


