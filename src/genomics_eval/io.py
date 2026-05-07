from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, TypeVar

import pandas as pd
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def ensure_parent(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def read_jsonl(path: str | Path) -> list[dict]:
    rows: list[dict] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: str | Path, rows: Iterable[dict | BaseModel]) -> None:
    ensure_parent(path)
    with Path(path).open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = row.model_dump() if isinstance(row, BaseModel) else row
            handle.write(json.dumps(payload, sort_keys=True) + "\n")


def model_rows(items: Iterable[BaseModel]) -> list[dict]:
    return [item.model_dump(mode="json") for item in items]


def write_parquet(path: str | Path, rows: Iterable[dict | BaseModel]) -> None:
    ensure_parent(path)
    payload = [row.model_dump(mode="json") if isinstance(row, BaseModel) else row for row in rows]
    pd.DataFrame(payload).to_parquet(path, index=False)


def read_parquet_records(path: str | Path) -> list[dict]:
    return pd.read_parquet(path).where(pd.notnull(pd.read_parquet(path)), None).to_dict("records")


def write_json(path: str | Path, payload: dict) -> None:
    ensure_parent(path)
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
