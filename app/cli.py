import json
import os
from pathlib import Path
from typing import Dict, List

from .db import (
    fetchall,
    insert_claim,
    insert_document,
    insert_extracted_field,
    log_audit,
    get_claim_id_by_number,
)
from .ingest import discover_documents, register_documents
from .extract import extract_text, extract_structured_fields
from .fraud import score_claim, persist_score
from .llm import generate_summary


def build_structured_map(claim_id: int) -> Dict[str, List[str]]:
    rows = fetchall(
        "SELECT field_name, field_value FROM extracted_fields WHERE claim_id=%s",
        (claim_id,),
    )
    structured: Dict[str, List[str]] = {}
    for r in rows:
        structured.setdefault(r["field_name"], []).append(r["field_value"])
    return structured


def collect_snippets(claim_id: int, limit: int = 3) -> List[str]:
    rows = fetchall(
        "SELECT content_text FROM documents WHERE claim_id=%s AND content_text IS NOT NULL LIMIT %s",
        (claim_id, limit),
    )
    return [r["content_text"][:1000] for r in rows if r.get("content_text")]


def run_pipeline(claim_number: str, policy_holder: str, claim_type: str, input_folder: str, incident_description: str | None = None, policy_number: str | None = None, **_ignored):
    existing = get_claim_id_by_number(claim_number)
    if existing:
        claim_id = existing
        # Optionally update metadata if changed
        from .db import execute
        execute(
            "UPDATE claims SET policy_holder=%s, claim_type=%s, incident_description=%s WHERE id=%s",
            (policy_holder, claim_type, incident_description, claim_id),
        )
    else:
        claim_id = insert_claim(claim_number, policy_holder, claim_type, incident_description)

    paths = discover_documents(input_folder)
    doc_ids = register_documents(claim_id, paths)

    # OCR/text extraction for each file and structured field extraction
    for doc_id, p in zip(doc_ids, paths):
        text = extract_text(p)
        if text.strip():
            # store text back to document row
            from .db import execute
            execute("UPDATE documents SET content_text=%s WHERE id=%s", (text, doc_id))
        extract_structured_fields(claim_id, doc_id, text)

    # Fraud score
    structured = build_structured_map(claim_id)
    # Ensure core identifiers are present for scoring/LLM even if extractors miss them
    if not structured.get("claim_number"):
        structured["claim_number"] = [claim_number]
    if policy_holder and not structured.get("policy_holder"):
        structured["policy_holder"] = [policy_holder]
    if policy_number:
        # Persist provided policy number as a claim-level extracted field
        insert_extracted_field(
            claim_id=claim_id,
            field_name="policy_number",
            field_value=policy_number,
            confidence=1.0,
            document_id=None,
        )
        structured.setdefault("policy_number", []).append(policy_number)
    score, risk, rule_hits = score_claim(structured)
    persist_score(claim_id, score, risk, rule_hits)

    # LLM summary
    tmpl = Path(__file__).with_name("prompt_template.txt").read_text(encoding="utf-8")
    prompt = tmpl.format(
        structured_json=json.dumps({
            "claim_number": claim_number,
            "policy_holder": policy_holder,
            "claim_type": claim_type,
            "incident_description": incident_description,
            "extracted": structured,
            "fraud": {"score": score, "risk": risk, "rules": rule_hits},
        }, ensure_ascii=False, indent=2),
        snippets="\n---\n".join(collect_snippets(claim_id))
    )
    summary = generate_summary(prompt)
    log_audit("llm_summary_generated", summary[:500], claim_id=claim_id)
    print(summary)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Claims IDP pipeline")
    parser.add_argument("--claim-number", required=True)
    parser.add_argument("--policy-holder", required=True)
    parser.add_argument("--claim-type", required=True)
    parser.add_argument("--input-folder", required=True)
    parser.add_argument("--incident-description", required=False, default=None)
    args = parser.parse_args()

    run_pipeline(
        claim_number=args.claim_number,
        policy_holder=args.policy_holder,
        claim_type=args.claim_type,
        input_folder=args.input_folder,
        incident_description=args.incident_description,
    )


