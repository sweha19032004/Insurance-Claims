## Fraud Scorecard (Simple Weighted Rules)

### Inputs from Documents
- Field presence/consistency: `policy_number`, `claim_number`
- Medical codes: unique count of `icd10_code`
- Dates: incident date vs. policy effective dates (if available)
- Policy identifiers (temporary vs. permanent prefixes)

### Rules and Weights
- Missing `claim_number`: +20
- Temporary policy pattern (e.g., prefix `TEMP-`): +25
- Many ICD-10 codes (> 5 unique): +15
- Date inconsistency (incident outside coverage period): +30

### Thresholds
- 0–24: LOW
- 25–49: MEDIUM
- 50+: HIGH

### Implementation Notes
- See `app/fraud.py` for the rule engine and persistence.
- Calibrate weights/thresholds using historical data; this is a starter baseline.


