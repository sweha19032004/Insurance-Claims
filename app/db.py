import os
import json
from typing import Any, Dict, Iterable, Optional, Tuple

# Optional MySQL; fallback to SQLite when unavailable
MYSQL_AVAILABLE = False
try:
    import mysql.connector  # type: ignore[import-not-found]
    MYSQL_AVAILABLE = True
except Exception:
    MYSQL_AVAILABLE = False

import sqlite3


USE_SQLITE = os.getenv("USE_SQLITE", "1" if not MYSQL_AVAILABLE else "0") == "1"


def _ensure_sqlite_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS claims (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          claim_number TEXT NOT NULL UNIQUE,
          policy_holder TEXT NOT NULL,
          claim_type TEXT NOT NULL,
          incident_description TEXT NULL,
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS documents (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          claim_id INTEGER NOT NULL,
          file_name TEXT NOT NULL,
          file_type TEXT NOT NULL,
          content_text TEXT NULL,
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS extracted_fields (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          claim_id INTEGER NOT NULL,
          document_id INTEGER NULL,
          field_name TEXT NOT NULL,
          field_value TEXT NOT NULL,
          confidence REAL NULL,
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
          FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS fraud_scores (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          claim_id INTEGER NOT NULL,
          score INTEGER NOT NULL,
          risk_level TEXT NOT NULL,
          rule_hits TEXT NULL,
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          claim_id INTEGER NULL,
          document_id INTEGER NULL,
          action TEXT NOT NULL,
          details TEXT NULL,
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    conn.commit()


def get_db_connection():
    if not USE_SQLITE:
        return mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", "root123"),
            database=os.getenv("MYSQL_DATABASE", "insurance")
        )
    db_path = os.getenv("SQLITE_PATH", os.path.join(os.path.dirname(__file__), "..", "insurance.db"))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    return conn


def _adapt_query(query: str) -> str:
    if USE_SQLITE:
        return "?".join(query.split("%s"))
    return query


def execute(query: str, params: Optional[Tuple[Any, ...]] = None) -> int:
    conn = get_db_connection()
    try:
        if USE_SQLITE:
            cur = conn.cursor()
            cur.execute(_adapt_query(query), params or ())
            conn.commit()
            return int(cur.lastrowid or 0)
        else:
            with conn.cursor() as cur:  # type: ignore[attr-defined]
                cur.execute(query, params or ())
                conn.commit()
                return cur.lastrowid or 0
    finally:
        conn.close()


def executemany(query: str, seq_params: Iterable[Tuple[Any, ...]]) -> None:
    conn = get_db_connection()
    try:
        if USE_SQLITE:
            cur = conn.cursor()
            cur.executemany(_adapt_query(query), list(seq_params))
            conn.commit()
        else:
            with conn.cursor() as cur:  # type: ignore[attr-defined]
                cur.executemany(query, list(seq_params))
                conn.commit()
    finally:
        conn.close()


def fetchone(query: str, params: Optional[Tuple[Any, ...]] = None):
    conn = get_db_connection()
    try:
        if USE_SQLITE:
            cur = conn.cursor()
            cur.execute(_adapt_query(query), params or ())
            row = cur.fetchone()
            return dict(row) if row is not None else None
        else:
            with conn.cursor(dictionary=True) as cur:  # type: ignore[attr-defined]
                cur.execute(query, params or ())
                return cur.fetchone()
    finally:
        conn.close()


def fetchall(query: str, params: Optional[Tuple[Any, ...]] = None):
    conn = get_db_connection()
    try:
        if USE_SQLITE:
            cur = conn.cursor()
            cur.execute(_adapt_query(query), params or ())
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        else:
            with conn.cursor(dictionary=True) as cur:  # type: ignore[attr-defined]
                cur.execute(query, params or ())
                return cur.fetchall()
    finally:
        conn.close()


def get_claim_id_by_number(claim_number: str) -> Optional[int]:
    row = fetchone("SELECT id FROM claims WHERE claim_number=%s", (claim_number,))
    if not row:
        return None
    # row may be dict for sqlite or MySQL dictionary cursor
    return int(row["id"]) if isinstance(row, dict) else int(row[0])


def insert_claim(claim_number: str, policy_holder: str, claim_type: str, incident_description: Optional[str]) -> int:
    return execute(
        "INSERT INTO claims (claim_number, policy_holder, claim_type, incident_description) VALUES (%s,%s,%s,%s)",
        (claim_number, policy_holder, claim_type, incident_description),
    )


def insert_document(claim_id: int, file_name: str, file_type: str, content_text: Optional[str]) -> int:
    return execute(
        "INSERT INTO documents (claim_id, file_name, file_type, content_text) VALUES (%s,%s,%s,%s)",
        (claim_id, file_name, file_type, content_text),
    )


def insert_extracted_field(claim_id: int, field_name: str, field_value: str, confidence: Optional[float], document_id: Optional[int] = None) -> int:
    return execute(
        "INSERT INTO extracted_fields (claim_id, document_id, field_name, field_value, confidence) VALUES (%s,%s,%s,%s,%s)",
        (claim_id, document_id, field_name, field_value, confidence),
    )


def insert_fraud_score(claim_id: int, score: int, risk_level: str, rule_hits: Dict[str, Any]):
    return execute(
        "INSERT INTO fraud_scores (claim_id, score, risk_level, rule_hits) VALUES (%s,%s,%s,%s)",
        (claim_id, score, risk_level, json.dumps(rule_hits)),
    )


def log_audit(action: str, details: str, claim_id: Optional[int] = None, document_id: Optional[int] = None):
    return execute(
        "INSERT INTO audit_logs (claim_id, document_id, action, details) VALUES (%s,%s,%s,%s)",
        (claim_id, document_id, action, details),
    )


