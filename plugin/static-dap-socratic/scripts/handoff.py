#!/usr/bin/env python3
"""Record a stage report and emit a handoff payload.

Usage:
    python3 handoff.py --report REPORT-hypotheses.md --token <token>

The hook issued the token when it injected the current stage. This script only
checks that the token is active and that the report payload exists; it does not
parse, score, or judge the report. The hook reads the recorded payload and
injects the next stage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("METHODOLOGY_HOME", str(Path.home() / ".zcode" / "methodology")))
TOKEN_DIR = HOME / "tokens"
HANDOFF_DIR = HOME / "handoff"
REPORTS_DIR = HOME / "reports"
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record a stage report and emit a handoff payload."
    )
    parser.add_argument("--report", required=True, help="Report file in the workspace")
    parser.add_argument("--token", required=True, help="Token from the current stage prompt")
    args = parser.parse_args()

    token = str(args.token or "").strip()
    if not TOKEN_RE.match(token):
        return fail("handoff token is not valid")

    token_path = TOKEN_DIR / f"{token}.json"
    if not token_path.exists():
        return fail("handoff token is not active")
    try:
        meta = json.loads(token_path.read_text(encoding="utf-8"))
    except Exception:
        return fail("handoff token is unreadable")

    expected = str(meta.get("report") or "")
    report = Path(str(args.report)).expanduser()
    if not report.is_absolute():
        report = (Path.cwd() / report).resolve()
    if not report.is_file():
        return fail(f"report missing: {report}")
    if report.stat().st_size <= 0:
        return fail(f"report empty: {report}")
    if expected and report.name.lower() != Path(expected).name.lower():
        return fail(f"report name mismatch: expected {expected}, got {report.name}")

    data = report.read_bytes()
    digest = hashlib.sha256(data).hexdigest()

    copy_dir = REPORTS_DIR / token
    copy_dir.mkdir(parents=True, exist_ok=True)
    copy_path = copy_dir / report.name
    shutil.copy2(report, copy_path)

    record = {
        "token": token,
        "session": str(meta.get("session") or ""),
        "stage": str(meta.get("stage") or ""),
        "epoch": meta.get("epoch", 0),
        "report": report.name,
        "report_original": str(report),
        "report_copy": str(copy_path),
        "sha256": digest,
        "excerpt": data.decode("utf-8", "replace")[:600],
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    record_path = HANDOFF_DIR / f"{token}.json"
    tmp = record_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(record_path)
    print(f"handoff accepted {token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
