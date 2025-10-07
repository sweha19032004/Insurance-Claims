from typing import Dict, List, Tuple

from .db import insert_fraud_score, log_audit


def score_claim(extracted: Dict[str, List[str]]) -> Tuple[int, str, Dict[str, int]]:
    score = 0
    rule_hits: Dict[str, int] = {}

    def hit(rule: str, points: int):
        nonlocal score
        score += points
        rule_hits[rule] = rule_hits.get(rule, 0) + points

    # Simple weighted rules (see docs/fraud_scorecard.md)
    if len(set(extracted.get("icd10_code", []))) > 5:
        hit("many_icd_codes", 15)

    # New lightweight rules to provide more gradient
    if extracted.get("icd10_code"):
        hit("icd_codes_present", 5)

    policy_numbers = [p for p in extracted.get("policy_number", []) if p]
    if not policy_numbers:
        hit("missing_policy_number", 10)
    elif len(set(policy_numbers)) > 1:
        hit("policy_number_inconsistent", 20)

    # Reward presence of core identifiers to avoid zero scores when extraction is minimal
    if extracted.get("claim_number"):
        hit("claim_number_present", 5)
    if policy_numbers:
        hit("policy_number_present", 5)

    if any(len(v) > 0 and v.startswith("TEMP-") for v in extracted.get("policy_number", [])):
        hit("temporary_policy_number", 25)

    if not extracted.get("claim_number"):
        hit("missing_claim_number", 20)

    # Normalize to risk level
    risk = "LOW"
    if score >= 50:
        risk = "HIGH"
    elif score >= 25:
        risk = "MEDIUM"

    return score, risk, rule_hits


def persist_score(claim_id: int, score: int, risk: str, rule_hits: Dict[str, int]):
    insert_fraud_score(claim_id, score, risk, rule_hits)
    log_audit("fraud_scored", f"score={score} risk={risk}", claim_id=claim_id)


