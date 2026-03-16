"""
bot_db.py — SQLite data layer for picoclaw.

Provides a thread-local connection and init_db() which creates all tables
using CREATE TABLE IF NOT EXISTS (safe to call on every startup).

Dependency chain: bot_config → bot_db  (no other bot_* imports here)
"""

import sqlite3
import threading
import os

from core.bot_config import log

# ── Database file path ────────────────────────────────────────────────────────
_PICOCLAW_DIR = os.path.expanduser("~/.picoclaw")
DB_PATH = os.path.join(_PICOCLAW_DIR, "pico.db")

# Thread-local storage for per-thread connections
_local = threading.local()

# ── Schema ────────────────────────────────────────────────────────────────────
_SCHEMA_SQL = """
-- Core user table (replaces registrations.json + users.json)
CREATE TABLE IF NOT EXISTS users (
    chat_id     INTEGER PRIMARY KEY,
    username    TEXT,
    name        TEXT,
    role        TEXT    DEFAULT 'pending',
    language    TEXT    DEFAULT 'ru',
    audio_on    INTEGER DEFAULT 0,
    created_at  TEXT    DEFAULT (datetime('now')),
    approved_at TEXT
);

-- Voice optimisation flags (replaces voice_opts.json)
CREATE TABLE IF NOT EXISTS voice_opts (
    chat_id              INTEGER PRIMARY KEY REFERENCES users(chat_id),
    silence_strip        INTEGER DEFAULT 0,
    low_sample_rate      INTEGER DEFAULT 0,
    warm_piper           INTEGER DEFAULT 0,
    parallel_tts         INTEGER DEFAULT 0,
    user_audio_toggle    INTEGER DEFAULT 0,
    tmpfs_model          INTEGER DEFAULT 0,
    vad_prefilter        INTEGER DEFAULT 0,
    whisper_stt          INTEGER DEFAULT 0,
    piper_low_model      INTEGER DEFAULT 0,
    persistent_piper     INTEGER DEFAULT 0,
    voice_timing_debug   INTEGER DEFAULT 0,
    vosk_fallback        INTEGER DEFAULT 1
);

-- Global voice optimisation flags (system-wide, not per-user)
CREATE TABLE IF NOT EXISTS global_voice_opts (
    key    TEXT PRIMARY KEY,
    value  INTEGER NOT NULL DEFAULT 0
);

-- Calendar events (replaces calendar/<chat_id>.json)
CREATE TABLE IF NOT EXISTS calendar_events (
    id                TEXT    PRIMARY KEY,
    chat_id           INTEGER,
    title             TEXT    NOT NULL,
    dt_iso            TEXT    NOT NULL,
    remind_before_min INTEGER DEFAULT 15,
    reminded          INTEGER DEFAULT 0,
    created_at        TEXT    DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_calendar_chat_dt
    ON calendar_events(chat_id, dt_iso);

-- Notes metadata index (content stays in .md files)
CREATE TABLE IF NOT EXISTS notes_index (
    slug        TEXT,
    chat_id     INTEGER,
    title       TEXT    NOT NULL,
    created_at  TEXT    DEFAULT (datetime('now')),
    updated_at  TEXT    DEFAULT (datetime('now')),
    PRIMARY KEY (slug, chat_id)
);

-- Per-user mail credentials (replaces mail_creds/<chat_id>.json)
CREATE TABLE IF NOT EXISTS mail_creds (
    chat_id      INTEGER PRIMARY KEY,
    provider     TEXT,
    email        TEXT,
    imap_host    TEXT,
    imap_port    INTEGER DEFAULT 993,
    password_enc TEXT,
    target_email TEXT,
    updated_at   TEXT    DEFAULT (datetime('now'))
);

-- Conversation history per user
CREATE TABLE IF NOT EXISTS chat_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id    INTEGER,
    role       TEXT    NOT NULL,
    content    TEXT    NOT NULL,
    created_at TEXT    DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_history_chat_time
    ON chat_history(chat_id, created_at);

-- TTS orphan cleanup tracker (replaces pending_tts.json)
CREATE TABLE IF NOT EXISTS tts_pending (
    chat_id    INTEGER PRIMARY KEY,
    msg_id     INTEGER NOT NULL,
    created_at TEXT    DEFAULT (datetime('now'))
);

-- Contacts
CREATE TABLE IF NOT EXISTS contacts (
    id          TEXT    PRIMARY KEY DEFAULT (lower(hex(randomblob(4)))),
    chat_id     INTEGER NOT NULL,
    name        TEXT    NOT NULL,
    phone       TEXT,
    email       TEXT,
    address     TEXT,
    notes       TEXT,
    created_at  TEXT    DEFAULT (datetime('now')),
    updated_at  TEXT    DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_contacts_chat_name
    ON contacts(chat_id, name COLLATE NOCASE);
"""


# ── Connection management ─────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    """Return a thread-local SQLite connection, creating it if needed."""
    if not getattr(_local, "conn", None):
        os.makedirs(_PICOCLAW_DIR, exist_ok=True)
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def init_db() -> None:
    """Create all tables on startup.  Safe to call every time — idempotent."""
    conn = get_db()
    conn.executescript(_SCHEMA_SQL)
    conn.commit()
    log.info(f"[DB] init OK : {DB_PATH}")


def close_db() -> None:
    """Close and discard the thread-local connection (used in tests and teardown)."""
    conn = getattr(_local, "conn", None)
    if conn:
        conn.close()
        _local.conn = None


_VOICE_OPT_KEYS = [
    "silence_strip", "low_sample_rate", "warm_piper", "parallel_tts",
    "user_audio_toggle", "tmpfs_model", "vad_prefilter", "whisper_stt",
    "vosk_fallback", "piper_low_model", "persistent_piper", "voice_timing_debug",
]


def db_save_voice_opts(opts: dict) -> None:
    """Persist all voice-opt flags to the global_voice_opts table."""
    conn = get_db()
    for key in _VOICE_OPT_KEYS:
        conn.execute(
            "INSERT INTO global_voice_opts(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, 1 if opts.get(key) else 0),
        )
    conn.commit()


def db_get_voice_opts() -> dict:
    """Return all voice-opt flags from the global_voice_opts table."""
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM global_voice_opts").fetchall()
    result = {row[0]: bool(row[1]) for row in rows}
    for key in _VOICE_OPT_KEYS:
        result.setdefault(key, False)
    return result
