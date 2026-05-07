from __future__ import annotations

import json
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from genomics_eval.schemas import AIOutput, EvalScore

MIGRATIONS = Path(__file__).with_name("migrations.sql")


def connect(path: str | Path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(MIGRATIONS.read_text(encoding="utf-8"))
    return conn


def write_run_metadata(
    db_path: str | Path,
    run_name: str,
    model_name: str = "mock",
    prompt_version: str = "v1",
    dataset_version: str = "local",
    clinvar_version: str = "subset",
) -> str:
    run_id = str(uuid.uuid4())
    conn = connect(db_path)
    try:
        conn.execute(
            "INSERT INTO eval_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                run_name,
                datetime.now(timezone.utc).isoformat(),
                _git_commit(),
                model_name,
                prompt_version,
                dataset_version,
                clinvar_version,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return run_id


def write_scores(db_path: str | Path, run_id: str, scores: list[EvalScore]) -> None:
    conn = connect(db_path)
    try:
        conn.executemany(
            "INSERT INTO eval_scores VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    run_id,
                    score.case_id,
                    score.passed,
                    score.gene_correct,
                    score.transcript_correct,
                    score.hgvs_correct,
                    score.classification_correct,
                    score.condition_correct,
                    score.hallucination_detected,
                    score.severity,
                    json.dumps(score.failure_modes),
                    score.notes,
                )
                for score in scores
            ],
        )
        conn.commit()
    finally:
        conn.close()


def write_ai_outputs(db_path: str | Path, run_id: str, outputs: list[AIOutput], prompts: dict[str, str]) -> None:
    conn = connect(db_path)
    try:
        conn.executemany(
            "INSERT INTO ai_outputs VALUES (?, ?, ?, ?, ?)",
            [
                (
                    run_id,
                    output.case_id,
                    prompts.get(output.case_id, ""),
                    output.response_text,
                    output.model_dump_json(),
                )
                for output in outputs
            ],
        )
        conn.commit()
    finally:
        conn.close()


def load_previous_run(db_path: str | Path) -> dict | None:
    conn = connect(db_path)
    try:
        row = conn.execute("SELECT * FROM eval_runs ORDER BY created_at DESC LIMIT 1").fetchone()
        if not row:
            return None
        return dict(zip([col[0] for col in conn.execute("SELECT * FROM eval_runs LIMIT 0").description], row))
    finally:
        conn.close()


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None
