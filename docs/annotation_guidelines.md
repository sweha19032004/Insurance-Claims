## Dataset Preparation and Annotation Guide

### Scope
Prepare a supervised dataset for medical reports, claim forms, and policy documents to train/evaluate extraction and classification models.

### File Organization
- Split into `train/`, `dev/`, `test/` directories.
- Each entry references source files via relative paths.

### Labels
- Document-level label: `document_type` ∈ {`claim_form`, `medical_report`, `policy_doc`, `invoice`, `other`}.
- Entity labels (fields to extract):
  - `policy_number`
  - `claim_number`
  - `icd10_code` (multiple allowed)
  - `incident_date`
  - `provider_name`
  - `insured_name`
  - `amount` (if invoice)
- Optional span-level offsets (character-based) for training sequence labellers.

### JSONL Schema (per document)
```json
{
  "id": "CLM-0001-001",
  "document_type": "medical_report",
  "file_path": "relative/path/to/medical_report.pdf",
  "fields": {
    "policy_number": {"value": "POL-123456", "confidence": 1.0},
    "claim_number": {"value": "CLM-0001", "confidence": 1.0},
    "icd10_code": [{"value": "S16.1"}, {"value": "M54.2"}],
    "incident_date": {"value": "2025-09-01"}
  },
  "spans": [
    {"label": "policy_number", "start": 120, "end": 129},
    {"label": "icd10_code", "start": 342, "end": 347}
  ]
}
```

### Annotation Tips
- Normalize codes to uppercase; trim whitespace and punctuation.
- For `icd10_code`, allow duplicates across pages but dedupe per document during evaluation.
- For dates, use ISO 8601 (`YYYY-MM-DD`).
- Use `unknown` if a field is not present.

### Quality Control
- Double-annotate 10% and adjudicate disagreements.
- Track inter-annotator agreement (Cohen's kappa) for `document_type` and entity spans.


