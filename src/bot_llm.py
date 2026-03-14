"""
bot_llm.py — Pluggable LLM backend abstraction.

Wraps the existing picoclaw CLI call in a clean interface that the web app
can import without pulling in Telegram dependencies.
"""

import os
import re
import subprocess
from pathlib import Path

from bot_config import PICOCLAW_BIN, PICOCLAW_CONFIG, ACTIVE_MODEL_FILE, log


# ─────────────────────────────────────────────────────────────────────────────
# Active model
# ─────────────────────────────────────────────────────────────────────────────

def get_active_model() -> str:
    """Return the admin-selected model name or empty string."""
    try:
        return Path(ACTIVE_MODEL_FILE).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def set_active_model(name: str) -> None:
    Path(ACTIVE_MODEL_FILE).write_text(name, encoding="utf-8")


def list_models() -> list[dict]:
    """Read model_list from picoclaw config.json."""
    import json
    try:
        cfg = json.loads(Path(PICOCLAW_CONFIG).read_text(encoding="utf-8"))
        return cfg.get("model_list", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Output cleaning  (ported from bot_access._clean_picoclaw_output)
# ─────────────────────────────────────────────────────────────────────────────

_ANSI_RE     = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_SPINNER_RE  = re.compile(r"[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏⣾⣽⣻⢿⡿⣟⣯⣷◐◑◒◓⠁⠂⠄⡀⢀⠠⠐⠈|/\\-]")
_PRINTF_WRAP = re.compile(r"^printf\s+['\"](.+)['\"]\s*$", re.DOTALL)
_LOG_PREFIX  = re.compile(r"^\d{4}[/-]\d{2}[/-]\d{2}[\sT]\d{2}:\d{2}:\d{2}\s*(INFO|DEBUG|WARN|ERROR)\s*", re.MULTILINE)
_PIPE_HEADER = re.compile(r"^(agent|picoclaw)\s*[|│]", re.MULTILINE | re.IGNORECASE)


def _clean_output(raw: str) -> str:
    text = _ANSI_RE.sub("", raw)
    text = _SPINNER_RE.sub("", text)
    text = _LOG_PREFIX.sub("", text)
    text = _PIPE_HEADER.sub("", text)
    m = _PRINTF_WRAP.match(text.strip())
    if m:
        text = m.group(1)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point — ask LLM
# ─────────────────────────────────────────────────────────────────────────────

def ask_llm(prompt: str, timeout: int = 60) -> str:
    """Call the picoclaw CLI and return the cleaned response text."""
    model = get_active_model()
    cmd = [PICOCLAW_BIN, "agent"]
    if model:
        cmd += ["--model", model]
    cmd += ["-m", prompt]

    env = {**os.environ, "NO_COLOR": "1"}
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, env=env,
        )
        if proc.returncode != 0:
            log.warning(f"[LLM] picoclaw rc={proc.returncode}: {proc.stderr[:200]}")
        raw = proc.stdout or proc.stderr or ""
        return _clean_output(raw)
    except subprocess.TimeoutExpired:
        log.warning(f"[LLM] picoclaw timed out ({timeout}s)")
        return ""
    except FileNotFoundError:
        log.error(f"[LLM] picoclaw binary not found: {PICOCLAW_BIN}")
        return ""
