from app.fraud import score_claim


def test_score_rules():
    extracted = {
        "icd10_code": ["S16.1", "M54.2", "A10", "B20", "C30", "D40"],
        "policy_number": ["TEMP-9999"],
        "claim_number": [],
    }
    score, risk, hits = score_claim(extracted)
    assert score >= 60  # 15 + 25 + 20
    assert risk == "HIGH"

