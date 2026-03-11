# AGENTS Instructions

## User Working Preferences
- Keep persistent operational knowledge in this file so future sessions can continue quickly.
- Use this file as the first reference for recurring document/accounting tasks.

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

## Recurring Accounting Task (Slovenia, Sintaris d.o.o.)
- Source directory to review: `G:\My Drive\Stas\SI\`
- Main source subfolders previously observed:
  - `Shared_Documents`
  - `Antraege`
  - `Contracts`
  - `Invoices`
  - `additional Info`
  - `Reisen`
  - `SINTARIS`
  - `Bank`
- Target directory to prepare for accountant: `G:\My Drive\Stas\SI\accounting_2025`
- Goal: collect invoices and all tax-relevant 2025 documents for preparing the 2025 tax declaration of `Sintaris d.o.o.` (Slovenia).

## Mail/Account Sources to Check for Relevant Documents
- `sintaris.comqgmail.com` (as provided by user)
- `stanislav.ulmer@gmail.com`

## Travel-Related Requirement
- Include documents for one private trip to Slovenia in the previous year.
- Search for invoices/costs tied to that trip and copy them into `accounting_2025`.

## Credentials Handling
- Credentials must be kept in `.env` only (already git-ignored).
- Never store secrets/passwords in this file.
- `.env` contains placeholders/fields for:
  - Host access credentials (LAN + Tailscale)
  - `cloud.dev2null.de` deployment credentials
  - Google account mail credentials (IMAP/SMTP + app passwords)
  - Optional Google OAuth credentials

## Execution Checklist (Accounting 2025)
1. Confirm source path exists: `G:\My Drive\Stas\SI\`
2. Create target path if missing: `G:\My Drive\Stas\SI\accounting_2025`
3. Create target subfolders:
   - `01_invoices`
   - `02_bank`
   - `03_contracts`
   - `04_travel_slovenia_private`
   - `05_tax_supporting_docs`
   - `06_email_exports`
4. Scan source folders for 2025-relevant files (PDF, DOCX, XLS/XLSX, CSV, images, ZIP exports).
5. Copy all invoice files into `01_invoices` (preserve originals; do not move/delete sources).
6. Copy bank/payment confirmations relevant to 2025 business activity into `02_bank`.
7. Copy contracts/agreements relevant to 2025 into `03_contracts`.
8. Identify the private Slovenia trip documents (transport, lodging, receipts, related costs) and copy into `04_travel_slovenia_private`.
9. Check local mail exports/data for:
   - `sintaris.comqgmail.com`
   - `stanislav.ulmer@gmail.com`
   Copy relevant attachments/exports to `06_email_exports`.
10. Copy other tax-supporting records for 2025 into `05_tax_supporting_docs`.
11. Generate an index file `accounting_2025\INDEX.txt` listing copied files grouped by folder.
12. Generate `accounting_2025\MISSING_ITEMS.txt` for unclear or missing documents.
13. Sanity check duplicates and obvious misfiles; keep uncertain items but mark them in `MISSING_ITEMS.txt`.
14. Never store credentials/tokens in `accounting_2025`; keep secrets only in `.env`.

- Source directory to review: `G:\My Drive\Stas\SI\`
- Main source subfolders previously observed:
  - `Shared_Documents`
  - `Antraege`
  - `Contracts`
  - `Invoices`
  - `additional Info`
  - `Reisen`
  - `SINTARIS`
  - `Bank`
- Target directory to prepare for accountant: `G:\My Drive\Stas\SI\accounting_2025`
- Goal: collect invoices and all tax-relevant 2025 documents for preparing the 2025 tax declaration of `Sintaris d.o.o.` (Slovenia).

## Mail/Account Sources to Check for Relevant Documents
- `sintaris.comqgmail.com` (as provided by user)
- `stanislav.ulmer@gmail.com`

## Travel-Related Requirement
- Include documents for one private trip to Slovenia in the previous year.
- Search for invoices/costs tied to that trip and copy them into `accounting_2025`.

## Credentials Handling
- Credentials must be kept in `.env` only (already git-ignored).
- Never store secrets/passwords in this file.
- `.env` contains placeholders/fields for:
  - Host access credentials
  - `cloud.dev2null.de` deployment credentials
  - Google account mail credentials (IMAP/SMTP + app passwords)
  - Optional Google OAuth credentials

## Execution Checklist (Accounting 2025)
1. Confirm source path exists: `G:\My Drive\Stas\SI\`
2. Create target path if missing: `G:\My Drive\Stas\SI\accounting_2025`
3. Create target subfolders:
   - `01_invoices`
   - `02_bank`
   - `03_contracts`
   - `04_travel_slovenia_private`
   - `05_tax_supporting_docs`
   - `06_email_exports`
4. Scan source folders for 2025-relevant files (PDF, DOCX, XLS/XLSX, CSV, images, ZIP exports).
5. Copy all invoice files into `01_invoices` (preserve originals; do not move/delete sources).
6. Copy bank/payment confirmations relevant to 2025 business activity into `02_bank`.
7. Copy contracts/agreements relevant to 2025 into `03_contracts`.
8. Identify the private Slovenia trip documents (transport, lodging, receipts, related costs) and copy into `04_travel_slovenia_private`.
9. Check local mail exports/data for:
   - `sintaris.comqgmail.com`
   - `stanislav.ulmer@gmail.com`
   Copy relevant attachments/exports to `06_email_exports`.
10. Copy other tax-supporting records for 2025 into `05_tax_supporting_docs`.
11. Generate an index file `accounting_2025\INDEX.txt` listing copied files grouped by folder.
12. Generate `accounting_2025\MISSING_ITEMS.txt` for unclear or missing documents.
13. Sanity check duplicates and obvious misfiles; keep uncertain items but mark them in `MISSING_ITEMS.txt`.
14. Never store credentials/tokens in `accounting_2025`; keep secrets only in `.env`.
