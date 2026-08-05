from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from models import ConfirmedCase, DrugExtraction, ValidationResult


def _db_path() -> Path:
    path = Path(os.getenv("AUDIT_DB_PATH", "./data/audit.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_db() -> None:
    with sqlite3.connect(_db_path()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS case_audit (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                transcript TEXT NOT NULL,
                field_note TEXT NOT NULL,
                ai_result_json TEXT NOT NULL,
                validation_json TEXT NOT NULL,
                confirmed_json TEXT NOT NULL
            )
            """
        )


def save_case(
    transcript: str,
    field_note: str,
    ai_result: DrugExtraction,
    validation: ValidationResult,
    confirmed: ConfirmedCase,
) -> str:
    init_db()
    case_id = str(uuid4())
    with sqlite3.connect(_db_path()) as conn:
        conn.execute(
            """
            INSERT INTO case_audit (
                id, created_at, transcript, field_note,
                ai_result_json, validation_json, confirmed_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                datetime.now().isoformat(timespec="seconds"),
                transcript,
                field_note,
                ai_result.model_dump_json(),
                validation.model_dump_json(),
                confirmed.model_dump_json(),
            ),
        )
    return case_id
