# Taris — Data Layer

**Version:** `2026.4.9`  
→ Architecture index: [architecture.md](../architecture.md)

---

## When to read this file
Changing data storage, adding a new table column, switching SQLite↔Postgres, modifying RAG indexing, or touching anything in `core/store*.py` or `core/bot_db.py`.

---

## Backend Selection

| `STORE_BACKEND` | Backend | Variant |
|---|---|---|
| `sqlite` (default) | `core/store_sqlite.py` + FTS5 | PicoClaw (Pi), lightweight |
| `postgres` | `core/store_postgres.py` + pgvector | OpenClaw (TariStation) |

**Change:** Set `STORE_BACKEND=postgres` + `DATABASE_URL=postgresql://...` in `~/.taris/bot.env`. Restart service.

**Entry point:** `from core.store import store` — all modules use only the factory singleton.

---

## Protocol interface (`store_base.py`)

All backends implement this. Do NOT import `store_sqlite` or `store_postgres` directly.

| Method | Key args | Used by |
|---|---|---|
| `index_document(chunks)` | list of chunk dicts | `bot_documents.py` |
| `search_fts(query, top_k)` | str, int | `bot_llm.py` (`_rag_context`) |
| `get_document_by_hash(chat_id, doc_hash)` | SHA256 hex | `bot_documents.py` (dedup) |
| `update_document_field(doc_id, field, value)` | str, str, any | `bot_documents.py` |
| `add_chat_history(chat_id, role, content)` | — | `bot_state.py` |
| `load_chat_history(chat_id)` | — | `bot_state.py` (startup) |
| `clear_chat_history(chat_id)` | — | `bot_state.py` |
| `add_summary(chat_id, tier, content)` | `'mid'`/`'long'` | `bot_state.py` |
| `list_summaries(chat_id)` | — | `bot_state.py` |

---

## SQLite schema (`core/bot_db.py` → `init_db()`)

| Table | Purpose | Key columns |
|---|---|---|
| `documents` | RAG doc registry | `doc_id, chat_id, filename, doc_hash, char_count, n_chunks, file_size_bytes, shared, metadata` |
| `document_chunks` | Chunk text storage | `chunk_id, doc_id, chunk_text, chunk_index` |
| `fts_documents` | FTS5 virtual table (BM25) | auto-indexed from `document_chunks` |
| `chat_history` | Conversation turns | `chat_id, role, content, created_at` |
| `conversation_summaries` | Tiered memory | `chat_id, tier (mid/long), summary, msg_count` |
| `notes_index` | Note metadata + content | `slug, chat_id, title, content, updated_at` (DB-primary v2026.3.31) |
| `contacts` | Contact book | `chat_id, name, phone, email` |
| `rag_log` | RAG retrieval audit | `chat_id, query, query_type, n_chunks, chars_injected, latency_ms, created_at` |
| `user_prefs` | Per-user settings | `chat_id, key, value` (e.g. `rag_top_k`, `rag_chunk_size`, `memory_enabled`) |
| `system_settings` | Admin-configured globals | `key, value` (e.g. `CONVERSATION_HISTORY_MAX`, `CONV_SUMMARY_THRESHOLD`) |
| `security_events` | Security audit log | `chat_id, event_type, detail, created_at` |
| `llm_calls` | LLM call trace | `chat_id, model, prompt_chars, response_chars, latency_ms, rag_chunks, context_snapshot` |

**Add a new column:** Add `ALTER TABLE ... ADD COLUMN ...` in `init_db()` — wrapped in `try/except OperationalError` for idempotency. See existing examples at `bot_db.py` lines ~85–100.

---

## Runtime data files

| File | Description |
|---|---|
| `~/.taris/taris.db` | SQLite DB (all tables above) |
| `~/.taris/rag_settings.json` | Runtime RAG params — read by `core/rag_settings.py` |
| `~/.taris/notes/<chat_id>/<slug>.md` | Note content (Markdown) |
| `~/.taris/calendar/<chat_id>.json` | Calendar events (legacy JSON file) |
| `~/.taris/accounts.json` | Web UI accounts (bcrypt + JWT) |
| `~/.taris/voice_opts.json` | Per-user voice flags |
| `~/.taris/llm_per_func.json` | Per-function LLM overrides |
| `~/.taris/bot.env` | All secrets + `STORE_BACKEND` + `DATABASE_URL` |

---

## Config constants (`bot_config.py`)

| Constant | Default | Description |
|---|---|---|
| `STORE_BACKEND` | `"sqlite"` | `sqlite` or `postgres` |
| `DATABASE_URL` | `""` | Postgres connection string |
| `RAG_ENABLED` | `true` | Master RAG on/off |
| `RAG_TOP_K` | `3` | Chunks per LLM call |
| `RAG_CHUNK_SIZE` | `512` | Chars per chunk at indexing |
| `CONV_SUMMARY_THRESHOLD` | `15` | Messages → trigger mid-tier summary |
| `CONV_MID_MAX` | `5` | Mid summaries → trigger long-tier compaction |

Runtime overrides: `core/rag_settings.py` reads `~/.taris/rag_settings.json` (set via Admin Panel).

---

## PostgreSQL extras (OpenClaw only)

- `pgvector` extension required: `CREATE EXTENSION IF NOT EXISTS vector;`  
- Embedding model: `all-MiniLM-L6-v2` (384-dim), loaded by `core/bot_embeddings.py`  
- Hybrid search: BM25 + cosine similarity combined  
- Install: see `src/setup/setup_llm_openclaw.sh`
- **Schema note**: PostgreSQL uses a single `vec_embeddings` table for both chunk text and embeddings (`chunk_text TEXT`, `embedding vector(384)`). There is **no** separate `doc_chunks` table (that is SQLite-only via FTS5 virtual table). `get_chunks_without_embeddings` queries `vec_embeddings WHERE embedding IS NULL`.
- **Shared docs**: `list_documents`, `search_fts`, `search_similar` all include `OR is_shared = 1` to ensure system documents (`chat_id=0`) are visible to every user. Fixed in v2026.4.9.

---

## ⏳ Open items

| Item | TODO ref |
|---|---|
| Full SQLite→Postgres migration script | [TODO.md §9](../TODO.md#9-flexible-storage-architecture-) |
| Calendar events: migrate from JSON files to DB table | [TODO.md §9](../TODO.md#9-flexible-storage-architecture-) |
