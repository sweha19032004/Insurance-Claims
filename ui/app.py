import os
import tempfile
from pathlib import Path
import sys
import json

try:
    import streamlit as st  # type: ignore[import-not-found]
except Exception as exc:
    raise ImportError("Missing dependency: streamlit. Install with: pip install streamlit") from exc

# Ensure project root is on sys.path when running from ui/ directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.cli import run_pipeline
from app.db import get_claim_id_by_number, fetchone


st.set_page_config(page_title="Claims IDP", layout="centered")
st.title("AI-Powered Insurance Claims Processing")

with st.form("upload_form"):
    claim_number = st.text_input("Claim Number", value="CLM-0001")
    policy_holder = st.text_input("Policy Holder", value="Jane Doe")
    claim_type = st.selectbox("Claim Type", ["Auto", "Health", "Home", "Travel"], index=0)
    policy_number_input = st.text_input("Policy Number (optional)", value="")
    incident_description = st.text_area("Incident Description", value="Rear-end collision on 2025-09-01")
    files = st.file_uploader("Upload documents (PDF, images, DOCX, TXT)", accept_multiple_files=True, type=["pdf","png","jpg","jpeg","tif","tiff","docx","txt"]) 
    submitted = st.form_submit_button("Process Claim")

if submitted:
    if not files:
        st.warning("Please upload at least one document.")
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / claim_number
            input_dir.mkdir(parents=True, exist_ok=True)
            for f in files:
                out = input_dir / f.name
                out.write_bytes(f.getvalue())

            with st.spinner("Running pipeline..."):
                # Capture stdout summary
                import io, sys
                buf = io.StringIO()
                old_stdout = sys.stdout
                sys.stdout = buf
                try:
                    run_pipeline(
                        claim_number=claim_number,
                        policy_holder=policy_holder,
                        claim_type=claim_type,
                        input_folder=str(input_dir),
                        incident_description=incident_description,
                        policy_number=policy_number_input.strip() or None,
                    )
                finally:
                    sys.stdout = old_stdout
                summary = buf.getvalue()

        st.subheader("Generated Summary")
        st.code(summary.strip() or "No summary produced.")

        # Fraud scorecard display
        try:
            claim_id = get_claim_id_by_number(claim_number)
            score_row = None
            if claim_id:
                score_row = fetchone(
                    "SELECT score, risk_level, rule_hits FROM fraud_scores WHERE claim_id=%s ORDER BY id DESC LIMIT 1",
                    (claim_id,)
                )
            if score_row:
                score = score_row["score"] if isinstance(score_row, dict) else score_row[0]
                risk = score_row["risk_level"] if isinstance(score_row, dict) else score_row[1]
                hits_raw = score_row["rule_hits"] if isinstance(score_row, dict) else score_row[2]
                try:
                    hits = json.loads(hits_raw) if isinstance(hits_raw, (str, bytes)) else hits_raw
                except Exception:
                    hits = {"raw": str(hits_raw)}

                st.subheader("Fraud Scorecard")
                st.metric(label="Fraud Score", value=int(score), delta=risk)
                st.write("Rule hits:")
                st.json(hits or {})
            else:
                st.info("No fraud score available for this claim yet.")
        except Exception as e:
            st.warning(f"Could not load fraud score: {e}")


