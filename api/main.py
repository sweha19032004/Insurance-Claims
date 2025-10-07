import sys
from pathlib import Path

try:
    from fastapi import FastAPI  # type: ignore[import-not-found]
except Exception as exc:
    raise ImportError("Missing dependency: fastapi. Install with: pip install fastapi uvicorn") from exc

try:
    from pydantic import BaseModel  # type: ignore[import-not-found]
except Exception as exc:
    raise ImportError("Missing dependency: pydantic. Install with: pip install pydantic") from exc

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.cli import run_pipeline
from app.db import fetchone


app = FastAPI(title="Claims IDP API")


class ProcessRequest(BaseModel):
    claim_number: str
    policy_holder: str
    claim_type: str
    input_folder: str
    incident_description: str | None = None


@app.post("/process")
def process_claim(req: ProcessRequest):
    run_pipeline(
        claim_number=req.claim_number,
        policy_holder=req.policy_holder,
        claim_type=req.claim_type,
        input_folder=req.input_folder,
        incident_description=req.incident_description,
    )
    return {"status": "ok", "claim_number": req.claim_number}


@app.get("/summary/{claim_number}")
def get_summary(claim_number: str):
    row = fetchone(
        "SELECT details FROM audit_logs WHERE action=%s AND claim_id=(SELECT id FROM claims WHERE claim_number=%s) ORDER BY id DESC LIMIT 1",
        ("llm_summary_generated", claim_number),
    )
    if not row:
        return {"summary": None}
    return {"summary": row["details"] if isinstance(row, dict) else row[0]}


