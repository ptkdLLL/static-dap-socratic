#!/usr/bin/env python3
"""Append-only hash-chained fact ledger.

Every relevant tool return is recorded by the hook. The ledger is the source of
facts; it does not judge relevance, evidence type, or sufficiency. The agent
reads facts and decides what to do next.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

HOME = Path(os.environ.get("METHODOLOGY_HOME", str(Path.home() / ".zcode" / "methodology")))
FACTS_DIR = HOME / "facts"


def _canonical(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(record: dict) -> str:
    payload = {k: v for k, v in record.items() if k != "hash"}
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def facts_path(session: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", str(session) or "anon")
    return FACTS_DIR / f"{safe}.jsonl"


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records: list[dict] = []
    prev = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("prev", "") != prev:
            raise ValueError("fact ledger prev mismatch")
        if record.get("hash") != _hash(record):
            raise ValueError("fact ledger hash mismatch")
        prev = record["hash"]
        records.append(record)
    return records


def append(path: Path, record: dict) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load(path)
    seq = (existing[-1]["seq"] + 1) if existing else 1
    item = dict(record)
    item["seq"] = seq
    item["fid"] = f"F#{seq}"
    item["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    item["prev"] = existing[-1]["hash"] if existing else ""
    item["hash"] = _hash(item)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    return item


def classify_tool(tool: str) -> str:
    low = (tool or "").lower()
    if "dap" in low:
        return "dap"
    if "codebase_memory" in low or "scip" in low:
        return "static"
    if tool == "Bash":
        return "bash"
    if tool == "Read":
        return "read"
    if tool in {"Write", "Edit", "ApplyPatch"}:
        return "write"
    return "other"


def target_tokens(text: str, limit: int = 40) -> list[str]:
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text or "")
    seen: list[str] = []
    for token in tokens:
        low = token.lower()
        if low not in seen:
            seen.append(low)
        if len(seen) >= limit:
            break
    return seen


def latest() -> Path | None:
    if not FACTS_DIR.exists():
        return None
    files = sorted(FACTS_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None
