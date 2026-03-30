# Taris — Security Architecture

**Version:** `2026.3.30+3`  
→ Architecture index: [architecture.md](../architecture.md)

## When to read this file
Modifying user roles, adding access guards, changing `bot_security.py`, `bot_access.py` or any `_is_*()` helper.

---

## 6.1 Three-Layer Prompt Injection Defense

**File:** `src/security/bot_security.py`

| Layer | Function | What it does |
|---|---|---|
| L1 — Pre-LLM scan | `_check_injection(text)` | Blocks ~25 regex patterns: instruction overrides, persona hijack, prompt extraction, credential leak, shell injection, jailbreak keywords (Russian+English). LLM never called on match. |
| L2 — User input delimiting | `_wrap_user_input(text)` | Wraps `[USER]\n{text}\n[/USER]` so LLM treats user text as data, not instructions. Called by `_user_turn_content()` in `bot_access.py`. |
| L3 — Security preamble | `SECURITY_PREAMBLE` constant | Prepended to every LLM call (role:system). Instructs model to not reveal credentials/paths, not generate shell commands, ignore role-override attempts. |

---

## 6.2 Role-Based Access Control

| Role | Guard function | Config source | Permissions |
|---|---|---|---|
| **Admin** | `_is_admin(chat_id)` | `ADMIN_USERS` in `bot.env` | All features + Admin panel + System chat + LLM settings |
| **Developer** | `_is_developer(chat_id)` | `DEVELOPER_USERS` in `bot.env` | Admin features + diagnostic tools + raw system info (since v2026.3.30) |
| **Full user** | `_is_allowed(chat_id)` | `ALLOWED_USERS` in `bot.env` | All user features (chat, voice, notes, calendar, contacts) |
| **Approved guest** | `_is_allowed(chat_id)` | `_dynamic_users` (DB) | All user features, dynamically approved by admin |
| **Pending** | `_is_pending(chat_id)` | `registrations` DB table | Registration confirmation only |
| **Blocked** | `reg.status == "blocked"` | `registrations` DB table | Blocked message only |

**File:** `src/telegram/bot_access.py` — all `_is_*()` functions.  
**File:** `src/telegram/bot_admin.py` — Admin panel entry point.

> ⏳ **OPEN:** Full per-feature RBAC (e.g. calendar-only users) → See [TODO.md §1.1](../TODO.md)

---

## 6.3 Admin Panel Access

| Feature | Role required | Guard |
|---|---|---|
| Admin panel button visible | admin | `_is_admin()` |
| System chat (NL→bash) | admin | `_is_admin()` + `_user_mode == "system"` |
| LLM settings (provider/model override) | admin | `_is_admin()` |
| Voice config admin view | admin | `_is_admin()` |
| User registration approval | admin | `_is_admin()` |
| RAG settings | admin | `_is_admin()` |
| Document admin (list/delete shared docs) | admin | `_is_admin()` |
| Diagnostic / raw system info | developer | `_is_developer()` |

---

## 6.4 Runtime Secrets

Secrets never in source code. All loaded from `~/.taris/bot.env` via `os.environ.get()` with safe defaults.

| Secret | Used by |
|---|---|
| `BOT_TOKEN` | `telebot.TeleBot(BOT_TOKEN)` |
| `ADMIN_USERS` | `_is_admin()` |
| `DEVELOPER_USERS` | `_is_developer()` |
| `ALLOWED_USERS` | `_is_allowed()` |
| `OPENAI_API_KEY` | `bot_llm.py` OpenAI provider |
| `DATABASE_URL` | `core/store_postgres.py` |
| `JWT_SECRET` | `src/security/bot_auth.py` (Web UI sessions) |
| `WEBCHAT_PWD_HASH` | Web UI local password auth |

> ⏳ **OPEN:** OAuth2 for Web UI → See [TODO.md §1](../TODO.md)

