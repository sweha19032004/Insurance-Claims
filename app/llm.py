import os
from typing import Dict, Any
import re
import json

try:
    import requests  # type: ignore[import-not-found]
except Exception as exc:
    requests = None  # type: ignore[assignment]


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")


def _fallback_summary_from_prompt(prompt: str) -> str:
    """Build a deterministic summary from embedded structured JSON in the prompt.
    This prevents crashes when the LLM API is unavailable.
    """
    try:
        # Expect block: 'Structured Data:\n{json}\n\nSnippets:'
        parts = prompt.split("Structured Data:\n", 1)
        if len(parts) < 2:
            return "LLM unavailable and no structured data found."
        after = parts[1]
        json_str = after.split("\n\nSnippets:", 1)[0].strip()
        data = json.loads(json_str)
        claim_number = data.get("claim_number") or "unknown"
        policy_holder = data.get("policy_holder") or "unknown"
        claim_type = data.get("claim_type") or "unknown"
        incident_description = data.get("incident_description") or "unknown"
        extracted = data.get("extracted") or {}
        codes = extracted.get("icd10_code") or []
        codes_str = ", ".join(sorted(set(codes))) if codes else "none"
        fraud = data.get("fraud") or {}
        risk = fraud.get("risk") or "LOW"
        issues = []
        if risk in ("MEDIUM", "HIGH"):
            issues.append(f"fraud risk {risk}")
        if not extracted.get("claim_number"):
            issues.append("missing claim number")
        if len(set(codes)) > 5:
            issues.append("many ICD-10 codes")
        issues_str = "\n- ".join([""] + issues) if issues else "none"
        return (
            f"Claim #: {claim_number}\n"
            f"Policy Holder: {policy_holder}\n"
            f"Type: {claim_type}\n"
            f"Summary: {incident_description}\n"
            f"Codes: {codes_str}\n"
            f"Issues: {issues_str}"
        ).strip()
    except Exception:
        return "LLM unavailable and fallback summary generation failed."


def _post_generate(prompt: str) -> str:
    """Try /api/generate first; if 404 or not supported, fall back to /api/chat; then to local fallback."""
    if requests is None:
        return _fallback_summary_from_prompt(prompt)
    # Prefer generate API
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        if resp.status_code == 404:
            raise FileNotFoundError("generate endpoint not found")
        if 200 <= resp.status_code < 300:
            data = resp.json()
            return data.get("response", "") or ""
        # Non-2xx: fallback
        raise RuntimeError(f"generate HTTP {resp.status_code}")
    except FileNotFoundError:
        # Fall back to chat API
        try:
            chat_payload = {
                "model": OLLAMA_MODEL,
                "stream": False,
                "messages": [
                    {"role": "system", "content": "You are a precise assistant summarizing insurance claims."},
                    {"role": "user", "content": prompt},
                ],
            }
            resp = requests.post(f"{OLLAMA_HOST}/api/chat", json=chat_payload, timeout=120)
            if 200 <= resp.status_code < 300:
                data = resp.json()
                msg = data.get("message") or {}
                return (msg.get("content") or data.get("response") or "").strip()
            # non-2xx
            return _fallback_summary_from_prompt(prompt)
        except Exception:
            return _fallback_summary_from_prompt(prompt)
    except Exception as e:
        return _fallback_summary_from_prompt(prompt)


def generate_summary(prompt: str) -> str:
    if os.getenv("DISABLE_LLM", "0") == "1":
        return "LLM disabled by configuration (DISABLE_LLM=1)."
    # Try generate, then chat
    return _post_generate(prompt)


