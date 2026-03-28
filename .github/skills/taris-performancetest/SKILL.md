---
name: taris-performancetest
description: >
  Run taris performance benchmarks (storage ops, menu navigation) locally
  and/or on Pi targets, merge results, and print a cross-platform comparison.
argument-hint: >
  platform: local | pi1 | pi2 | all (default: local)
  suite: storage | menus | all (default: all)
  n: iterations (default: 500 for storage, 100 for menus; use 50 for quick)
---

## When to Use

Run benchmarks when:
- A storage change was made (`bot_db.py`, `store_sqlite.py`, JSON data layer)
- A menu handler was optimized or refactored
- Performance regression is suspected
- Before/after comparing two implementations

---

## Quick Reference

| Command | What it does |
|---|---|
| `python tools/benchmark_suite.py` | All suites, local dev machine |
| `python tools/benchmark_suite.py --suite storage` | Storage ops only |
| `python tools/benchmark_suite.py --suite menus` | Menu latency only |
| `python tools/benchmark_suite.py --platform pi1` | All suites on PI1 |
| `python tools/benchmark_suite.py --platform pi2` | All suites on PI2 |
| `python tools/benchmark_suite.py --platform all` | Local + PI1 + PI2 |
| `python tools/benchmark_suite.py --compare` | Print table, no re-run |
| `python tools/benchmark_suite.py -n 50` | Quick run (50 iterations) |

---

## Step 1 — Local sanity check (fast)

```bash
cd /home/stas/projects/sintaris-pl
python3 tools/benchmark_suite.py --suite all --platform local -n 200
```

- ✅ no `⚠️` flags → no regression
- ⚠️ flag on a metric → >20% slower than previous same-platform run → investigate
- ❌ FAILED → import error; check `PYTHONPATH=src`

---

## Step 2 — PI1 run

```bash
# Ensure HOSTPWD is set in environment or .env
python3 tools/benchmark_suite.py --platform pi1
```
The suite auto-deploys the script to PI1, runs it, and merges results into `tools/benchmark_results.json`.

---

## Step 3 — PI2 run

```bash
python3 tools/benchmark_suite.py --platform pi2
```

---

## Step 4 — Full cross-platform comparison

```bash
python3 tools/benchmark_suite.py --platform all
```

---

## What Each Suite Measures

### `storage` (default 500 iterations)

| Operation | Backend |
|---|---|
| Voice opts read/write | JSON file (`voice_opts.json`) |
| Registrations load | JSON file |
| Contact upsert/lookup | SQLite (`bot_db.py`) |
| Calendar load/save | JSON file |
| Note save/read | JSON file |
| Batch contact upsert ×10 | SQLite |

### `menus` (default 100 iterations)

| TC | Handler | I/O |
|---|---|---|
| TC01–02 | `_menu_keyboard` admin/user | None |
| TC03 | `_send_menu` | Mocked send_message |
| TC04 | `_handle_notes_menu` | None |
| TC05–06 | `_handle_note_list` 0/10 notes | JSON dir scan |
| TC07–08 | `_handle_admin_menu / _list_users` | JSON |
| TC09–10 | `_handle_calendar_menu` 0/10 events | JSON |
| TC11–12 | `_handle_contacts_menu` 0/10 contacts | SQLite COUNT |
| TC13 | `_handle_contact_list` 10 contacts | SQLite SELECT |

---

## Pass / Warn / Fail

| Status | Condition | Action |
|---|---|---|
| ✅ PASS | All metrics within 20% of previous run | None |
| ⚠️ WARN | Any metric >20% slower | Re-run to confirm; investigate if persistent |
| ❌ FAIL | Script exits non-zero | Fix import/runtime error |

---

## Results File

`tools/benchmark_results.json` — JSON array, append-only.

Commit this file together with any change that causes a measurable performance shift — the comparison table always uses the *prior entry from the same node* as reference.

---

## After Running

1. ⚠️ regressions found → investigate before committing code changes.
2. Commit `tools/benchmark_results.json` with performance-affecting code changes.
3. New baseline established simply by committing the updated results file.
