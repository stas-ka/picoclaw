# AGENTS Instructions

## User Working Preferences
- Keep persistent operational knowledge in this file so future sessions can continue quickly.
- Use this file as the first reference for recurring document/accounting tasks.
- **Testing ("test software" / "run tests" / "verify changes"):** always read `doc/test-suite.md` first — it has the complete decision table, all run commands, and the Copilot chat-mode protocol. Never scan test files manually every session.

## Remote Host Access

| Key | Value |
|---|---|
| `TARGETHOST` | `OpenClawPI` |
| `HOSTUSER` | `stas` |
| `HOSTPWD` | *(see `.env`)* |
| `TAILSCALE_IP` | `100.81.143.126` |
| `TAILSCALE_HOST` | `openclawpi` |

- **LAN only:** `ssh stas@OpenClawPI` (works only on home network)
- **Remote (anywhere):** `plink -pw "%HOSTPWD%" -batch stas@100.81.143.126 "<cmd>"`
- Tailscale account: `stas.ulmer@` — Tailscale must be running on both devices
- Tailscale installed on Pi: v1.94.2 (installed 2026-03-10, service `tailscaled` auto-starts)

## Current Bot Version

`BOT_VERSION = "2026.3.25"` — deployed 2026-03-10

## Calendar Features (v2026.3.25)

### New: Multi-Event Add
- LLM prompt returns `{"events": [{title, dt}, ...]}` (always an array)
- 1 event → normal single confirm flow
- N events → sequential "1 of N" confirmation with **Save / Skip / Save All**
- `_pending_cal[chat_id]` step `"multi_confirm"` holds `{events: list, idx: int}`

### New: NL Query
- `_handle_calendar_query(chat_id, text)` — LLM extracts `{from, to, label}` date range
- Activated from console mode or callable directly
- Filters `_cal_load()` and displays countdown list

### New: Delete Confirmation
- `cal_del:<id>` → `_handle_cal_delete_request()` — shows confirmation card
- `cal_del_confirm:<id>` → `_handle_cal_delete_confirmed()` — actual deletion
- All calendar deletes require explicit confirmation

### New: Calendar Console Mode
- Button **💬 Консоль** in calendar menu → `_start_cal_console()`
- `_user_mode = "cal_console"` — free-form text processed by `_handle_cal_console()`
- LLM classifies intent: `add | query | delete | edit`
- All mutations still go through confirmation step

### Rule: All Calendar Mutations Need Confirmation
Apply this rule when adding new calendar features: add → confirm card → save; delete → confirm card → delete; edit → show updated card → confirm.

---

## Vibe Coding Protocol — MANDATORY

**After every completed user request** (any implementation, refactor, fix, or doc task), append an entry to `doc/vibe-coding-protocol.md`.

### What to record

| Field | How to measure |
|---|---|
| `Time` | UTC timestamp of the **user message** that triggered the work (from `<current_datetime>` tag) |
| `Request` | One-line description of what the user asked |
| `Complexity` | 1–5 scale (see below) |
| `Requests used` | Number of user→assistant turns for this item (count from first message to done) |
| `Model` | Model ID used (from `<model_information>` tag, e.g. `claude-sonnet-4.6`) |
| `Files changed` | Comma-separated list of files modified/created |
| `Status` | `done` / `partial` / `wip` |

### Complexity scale

| Score | Meaning |
|---|---|
| 1 | Trivial — one-liner, doc tweak, single string change |
| 2 | Simple — single file, < 20 lines, no logic change |
| 3 | Medium — multi-file or new function, < 100 lines |
| 4 | Complex — new feature, multi-file refactor, 100–500 lines |
| 5 | Very complex — architecture change, > 500 lines, or multiple interdependent systems |

### When to write

- **At the end of each completed request** — append a row to the current session block.
- If a request spans multiple turns before completion, record it once when done.
- If a session ends mid-task (`wip`), record what was done so far.
- **Do NOT skip** — this is the single source of measurement data for vibe coding cost analysis.

### Protocol file location

`doc/vibe-coding-protocol.md` — already exists, append to the current session block.

### Row format (append inside current session table)

```markdown
| HH:MM UTC | <request description> | <1–5> | <N turns> | claude-sonnet-4.6 | file1.py, file2.json | done |
```
