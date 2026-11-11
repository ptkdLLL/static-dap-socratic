#!/usr/bin/env python3
"""Report-handshake supervisor for the static+DAP methodology.

The hook injects exactly one stage prompt at a time, records facts, and advances
only when the current stage's report handoff exists. It never judges evidence,
never parses reports, and never denies a tool call.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("METHODOLOGY_HOME", str(Path.home() / ".zcode" / "methodology")))
STATE_DIR = HOME / "state"
TOKEN_DIR = HOME / "tokens"
HANDOFF_DIR = HOME / "handoff"
REPORTS_DIR = HOME / "reports"
ERRORS = HOME / "errors.log"
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
ACTIVATION = "基于静态工具与dap联合"

sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
try:
    import ledger
    import stages
except Exception:  # pragma: no cover
    ledger = None
    stages = None

SOURCE_EXTS = {
    ".kt", ".kts", ".java", ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp",
    ".m", ".mm", ".rs", ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".cs",
    ".swift", ".scala", ".gradle", ".cmake", ".sql", ".sh",
}

TMP_PREFIXES = ("/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/")

PRE_INDEX_READ_CARD = """[workflow] 全局索引前直接读源码，会把全局问题压成局部片段：你看到的是这一段，不是它在调用链/guard/生命周期里的位置。
先建索引、看架构和调用关系，再决定读哪 20 行；如果这次读取确实必要，说明理由。"""

BARE_GREP_CARD = "[workflow] " + (
    stages.BARE_GREP_RULE
    if stages is not None
    else "禁止在文档与日志以外的情况裸 grep；对于代码库，应该基于静态工具 MCP，使用优雅的方法探索以获得最佳效率。"
) + "\n对于当前这个问题，你认为如何使用静态工具才能更好地探索代码库、对项目与用户问题建立整体认识？"

SED_AWK_CARD = "[workflow] " + (
    stages.SED_AWK_RULE
    if stages is not None
    else "禁止用 awk/sed 整段读取代码；对于代码库，应该基于静态工具 MCP，使用优雅的方法探索以获得最佳效率。"
) + "\n对于当前这段代码，你认为应该先用静态工具确认哪些符号、调用关系和数据形状，再读哪一段窄窗？"

FULL_READ_CARD = """[workflow] 你已经建了索引，但还在整文件读。整文件读会把调用关系、数据形状、生命周期压成线性文本。
先用 trace_path/search_graph 拿 file:line，再读 ≤20 行；如果这个文件确实需要整体看，说明理由。"""

INDEX_STALE_NUDGE = """[workflow] 代码已改，当前索引可能过期；建议在本阶段结束前重新索引当前项目（codebase_memory index_repository 或 cscope/AST 重建），再继续需要全局结构的判断。"""


def session_id(data: dict) -> str:
    return str(data.get("session_id") or data.get("sessionId") or "anon")


def state_path(sid: str) -> Path:
    digest = hashlib.sha256(sid.encode("utf-8")).hexdigest()[:16]
    return STATE_DIR / f"{digest}.json"


def default_state() -> dict:
    return {
        "version": 2,
        "active": False,
        "stage": "S1",
        "epoch": 0,
        "token": "",
        "report": "",
        "consumed": True,
        "global_indexed": False,
        "index_fresh": False,
        "anti": {
            "pre_index_paths": [],
            "grep_count": 0,
            "grep_reminded": 0,
            "sed_count": 0,
            "sed_reminded": 0,
            "full_read_paths": [],
            "full_read_count": 0,
            "stale_nudged_stage": "",
        },
    }


def ensure(state: dict) -> dict:
    base = default_state()
    if not isinstance(state, dict):
        return base
    if state.get("version") != 2:
        return base
    for key, value in state.items():
        if key == "anti" and isinstance(value, dict):
            anti = dict(base["anti"])
            anti.update(value)
            base["anti"] = anti
        else:
            base[key] = value
    return base


def load_state(sid: str) -> dict:
    try:
        return ensure(json.loads(state_path(sid).read_text(encoding="utf-8")))
    except OSError:
        return default_state()
    except Exception:
        return default_state()


def save_state(sid: str, state: dict) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        path = state_path(sid)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def token_path(token: str) -> Path:
    return TOKEN_DIR / f"{token}.json"


def handoff_path(token: str) -> Path:
    return HANDOFF_DIR / f"{token}.json"


def issue_token(sid: str, state: dict, stage: str) -> None:
    state["stage"] = stage
    state["epoch"] = int(state.get("epoch", 0)) + 1
    if stage == "DONE" or stages is None:
        state["token"] = ""
        state["report"] = ""
        state["consumed"] = True
        save_state(sid, state)
        return
    token = secrets.token_hex(8)
    expected = stages.report_for(stage) or ""
    state["token"] = token
    state["report"] = expected
    state["consumed"] = False
    write_json_atomic(
        token_path(token),
        {
            "session": sid,
            "stage": stage,
            "epoch": state["epoch"],
            "report": expected,
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
    )
    save_state(sid, state)


def stage_prompt(state: dict) -> str:
    if stages is None:
        return ""
    return stages.prompt_for(state.get("stage", ""), str(PLUGIN_ROOT), state.get("token", ""))


def emit_stage(sid: str, state: dict, event: str) -> None:
    prompt = stage_prompt(state)
    save_state(sid, state)
    if prompt:
        emit(event, prompt)


def normalize_prompt(text: str) -> str:
    return re.sub(r"\s+", "", text or "").lower()


def is_activation(prompt: str) -> bool:
    return ACTIVATION in normalize_prompt(prompt)


def emit(event: str, text: str) -> None:
    payload = {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


def emit_pre(text: str) -> None:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "workflow reminder",
            "additionalContext": text,
        }
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


def tool_name(data: dict) -> str:
    return str(data.get("tool_name") or data.get("tool") or "")


def tool_input(data: dict) -> dict:
    raw = data.get("tool_input") or data.get("toolInput") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}
    return raw if isinstance(raw, dict) else {}


def tool_output(data: dict) -> str:
    raw = data.get("tool_response")
    if raw is None:
        raw = data.get("tool_output")
    if raw is None:
        raw = data.get("error")
    if isinstance(raw, dict):
        try:
            return json.dumps(raw, ensure_ascii=False)
        except Exception:
            return str(raw)
    return str(raw or "")


def path_of(inp: dict) -> str:
    return str(inp.get("file_path") or inp.get("path") or inp.get("file") or "")


def is_source(path: str) -> bool:
    low = str(path).lower()
    if any(low.startswith(prefix) for prefix in TMP_PREFIXES):
        return False
    return Path(path).suffix.lower() in SOURCE_EXTS


def is_test_path(path: str) -> bool:
    low = path.lower()
    return any(token in low for token in ("/test/", "/androidtest/", "test.kt", "test.java"))


def looks_like_global_index(tool: str, inp: dict) -> bool:
    if "codebase_memory" in tool:
        return tool.split("__")[-1] in {"index_repository", "index_status", "get_architecture"}
    if "scip" in tool:
        return True
    if tool == "Bash":
        command = str(inp.get("command", ""))
        return bool(re.search(r"\b(cscope|clang\s+-Xclang\s+-ast-dump)\b", command))
    return False


def looks_like_fresh_index(tool: str, inp: dict) -> bool:
    """A real refresh, not just a status/architecture read."""
    if "codebase_memory" in tool:
        return tool.split("__")[-1] == "index_repository"
    if "scip" in tool:
        return "index" in tool.split("__")[-1].lower()
    if tool == "Bash":
        command = str(inp.get("command", ""))
        return bool(re.search(r"\bcscope\s+.*\s-[bR]\b|\bclang(?:\+\+)?\s+.*-Xclang\s+-ast-dump\b", command))
    return False


def looks_like_grep(tool: str, inp: dict) -> bool:
    if tool == "Grep":
        return True
    if tool != "Bash":
        return False
    command = str(inp.get("command", ""))
    return bool(re.search(r"(^|[|;&\s])(grep|egrep|fgrep|rg)(\s|$)", command, re.IGNORECASE))


def looks_like_sed_awk(tool: str, inp: dict) -> bool:
    if tool != "Bash":
        return False
    command = str(inp.get("command", ""))
    return bool(re.search(r"(^|[|;&\s])(sed|awk)(\s|$)", command, re.IGNORECASE))


DATA_MARKERS = (
    "unzip", "zipinfo", "logcat", "strings",
    "/volumes/", "/sdcard/",
    ".log", ".txt", ".csv", ".epub", ".md",
    "readme", "/docs/", "docs/",
)

CACHE_PATH_MARKERS = (
    "/.gradle/", "~/.gradle", "/cellar/", "gradle/wrapper",
    "gradle-completion", "/.android/", "/library/android/sdk/",
)


def is_data_command(tool: str, inp: dict) -> bool:
    command = str(inp.get("command", "")).lower()
    path = path_of(inp).lower()
    text = command + " " + path
    return any(marker in text for marker in DATA_MARKERS)


def is_code_target(tool: str, inp: dict) -> bool:
    """Blacklist: grep/sed/awk whose object looks like a code file/repo path."""
    if tool == "Grep":
        if is_data_command(tool, inp):
            return False
        return True
    if tool != "Bash":
        return False
    if is_data_command(tool, inp):
        return False
    command = str(inp.get("command", "")).lower()

    # Filtering command output (ls/find/which/ps/env) is not codebase exploration.
    if re.search(r"\b(ls|find|which|ps|env|echo|printf)\b[^|]*\|\s*(grep|egrep|fgrep|rg)\b", command):
        return False

    # Tool/cache paths are not source files.
    cleaned = command
    for token in CACHE_PATH_MARKERS:
        cleaned = cleaned.replace(token, " ")

    if any(token in cleaned for token in ("/app/src", "app/src", "/src/", " src/")):
        return True
    for ext in SOURCE_EXTS:
        if re.search(r"[\w./-]+" + re.escape(ext) + r"\b", cleaned):
            return True

    # Repo-wide blind grep: recursive grep or rg without an explicit source target.
    if re.search(r"(^|[|;&\s])(grep|egrep|fgrep)\b[^|]*\s-[a-zA-Z]*[rR][a-zA-Z]*\b", cleaned):
        return True
    if re.search(r"(^|[|;&\s])rg\b", cleaned):
        return True
    return False


def read_is_full(inp: dict) -> bool:
    limit = inp.get("limit")
    if limit is None:
        return True
    try:
        return int(limit) > 80
    except (TypeError, ValueError):
        return True


def file_is_small(path: str) -> bool:
    try:
        return Path(path).stat().st_size <= 8000
    except OSError:
        return False


def record_fact(sid: str, tool: str, inp: dict, output: str) -> dict | None:
    if ledger is None:
        return None
    kind = ledger.classify_tool(tool)
    if kind == "other":
        return None
    op = tool.split("__")[-1] if "__" in tool else tool
    low = output.lower()
    explicit_error = any(token in low for token in (
        '"iserror": true', '"error":', "timed out", "timeout", "jdwp closed",
        "no frame", "no thread", "no such session", "not defined",
    ))
    record = {
        "session": sid,
        "tool": tool,
        "kind": kind,
        "op": op,
        "input": json.dumps(inp, ensure_ascii=False)[:2000],
        "result": output[:3000],
        "ok": not explicit_error,
        "value": "",
        "dap_session": inp.get("sessionId") or inp.get("session_id"),
    }
    try:
        return ledger.append(ledger.facts_path(sid), record)
    except OSError:
        return None


def record_handoff(sid: str, record: dict) -> None:
    if ledger is None:
        return
    try:
        ledger.append(
            ledger.facts_path(sid),
            {
                "session": sid,
                "tool": "handoff",
                "kind": "handoff",
                "op": "handoff",
                "stage": record.get("stage", ""),
                "epoch": record.get("epoch", 0),
                "report": record.get("report", ""),
                "report_copy": record.get("report_copy", ""),
                "sha256": record.get("sha256", ""),
                "excerpt": record.get("excerpt", ""),
                "input": "",
                "result": "accepted",
                "ok": True,
                "value": "",
            },
        )
    except OSError:
        pass


def maybe_process_handoff(sid: str, state: dict) -> bool:
    if not state.get("active") or state.get("stage") == "DONE" or state.get("consumed", True):
        return False
    token = str(state.get("token") or "")
    if not token:
        return False
    record_path = handoff_path(token)
    if not record_path.exists():
        return False
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if str(record.get("token") or "") != token:
        return False
    if str(record.get("stage") or "") != str(state.get("stage") or ""):
        return False
    report_copy = str(record.get("report_copy") or "")
    if not report_copy or not Path(report_copy).is_file():
        return False

    record_handoff(sid, record)
    nxt = stages.next_stage(state.get("stage", "")) if stages is not None else None

    state["consumed"] = True
    try:
        record_path.unlink()
    except OSError:
        pass
    try:
        token_path(token).unlink()
    except OSError:
        pass

    if not nxt or nxt == "DONE":
        state["stage"] = "DONE"
        state["token"] = ""
        state["report"] = ""
        state["consumed"] = True
        save_state(sid, state)
        emit("PostToolUse", stages.prompt_for("DONE", str(PLUGIN_ROOT), "") if stages else "")
        return True

    issue_token(sid, state, nxt)
    emit_stage(sid, state, "PostToolUse")
    return True


def handle_prompt(data: dict) -> None:
    prompt = data.get("prompt") or data.get("user_prompt") or ""
    if not prompt:
        return
    sid = session_id(data)
    state = load_state(sid)
    if is_activation(prompt):
        if state.get("active") and state.get("stage") != "DONE":
            return
        state = default_state()
        state["active"] = True
        state["epoch"] = 0
        issue_token(sid, state, "S1")
        emit_stage(sid, state, "UserPromptSubmit")
        return
    # Already-active sessions are not re-anchored on every user message: the
    # stage prompt is already in context, and repeated cards dilute attention.
    return


def handle_session(data: dict) -> None:
    sid = session_id(data)
    state = load_state(sid)
    if not state.get("active") or state.get("stage") == "DONE":
        return
    token = str(state.get("token") or "")
    if not token or not token_path(token).exists():
        issue_token(sid, state, state.get("stage", "S1"))
    emit_stage(sid, state, "SessionStart")


def handle_pre(data: dict) -> None:
    sid = session_id(data)
    state = load_state(sid)
    if not state.get("active") or state.get("stage") == "DONE":
        return
    tool = tool_name(data)
    inp = tool_input(data)
    path = path_of(inp)
    anti = state.setdefault("anti", {})

    if tool == "Read" and is_source(path):
        if not state.get("global_indexed") and path not in anti.get("pre_index_paths", []):
            anti.setdefault("pre_index_paths", []).append(path)
            save_state(sid, state)
            emit_pre(PRE_INDEX_READ_CARD)
            return
        if state.get("global_indexed") and read_is_full(inp) and not file_is_small(path):
            if path not in anti.get("full_read_paths", []):
                anti.setdefault("full_read_paths", []).append(path)
                anti["full_read_count"] = anti.get("full_read_count", 0) + 1
                save_state(sid, state)
                emit_pre(FULL_READ_CARD)
                return

    if looks_like_grep(tool, inp) and is_code_target(tool, inp):
        anti["grep_count"] = anti.get("grep_count", 0) + 1
        anti["grep_reminded"] = anti.get("grep_reminded", 0) + 1
        save_state(sid, state)
        emit_pre(BARE_GREP_CARD)
        return

    if looks_like_sed_awk(tool, inp) and is_code_target(tool, inp):
        anti["sed_count"] = anti.get("sed_count", 0) + 1
        anti["sed_reminded"] = anti.get("sed_reminded", 0) + 1
        save_state(sid, state)
        emit_pre(SED_AWK_CARD)
        return

    if tool in {"Write", "Edit", "ApplyPatch"} and is_source(path) and not is_test_path(path):
        if state.get("index_fresh"):
            state["index_fresh"] = False
            if anti.get("stale_nudged_stage") != state.get("stage"):
                anti["stale_nudged_stage"] = state.get("stage")
                save_state(sid, state)
                emit_pre(INDEX_STALE_NUDGE)
                return
        save_state(sid, state)
        return

    save_state(sid, state)


def handle_post(data: dict) -> None:
    sid = session_id(data)
    state = load_state(sid)
    if not state.get("active"):
        return
    tool = tool_name(data)
    inp = tool_input(data)
    output = tool_output(data)
    record = record_fact(sid, tool, inp, output)

    if looks_like_fresh_index(tool, inp) and (record is None or record.get("ok", True)):
        state["global_indexed"] = True
        state["index_fresh"] = True
    elif looks_like_global_index(tool, inp):
        state["global_indexed"] = True

    if tool in {"Write", "Edit", "ApplyPatch"} and is_source(path_of(inp)) and not is_test_path(path_of(inp)):
        state["index_fresh"] = False

    if maybe_process_handoff(sid, state):
        return
    save_state(sid, state)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "prompt"
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    try:
        if mode == "session":
            handle_session(data)
        elif mode == "prompt":
            handle_prompt(data)
        elif mode == "pre":
            handle_pre(data)
        elif mode == "post":
            handle_post(data)
    except Exception as exc:
        try:
            HOME.mkdir(parents=True, exist_ok=True)
            with ERRORS.open("a", encoding="utf-8") as handle:
                handle.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {mode}: {exc!r}\n")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
