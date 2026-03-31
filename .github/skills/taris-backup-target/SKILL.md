---
name: taris-backup-target
description: >
  Backup a Raspberry Pi target (data, software, system config, binaries, or all).
  Use before any deploy, migration, or schema change.
argument-hint: >
  host: OpenClawPI | OpenClawPI2 (default: OpenClawPI)
  type: data | software | system | binaries | all (default: all)
  path: local destination (default: ./backup/snapshots/)
---

## When to Use

| Trigger | Minimal type |
|---|---|
| Before any `deploy-to-target` or `safe-update` | `data` |
| Before schema migration | `data` |
| After Pi re-image | `all` |
| Periodic snapshot | `all` |

---

## Step 0 — Read credentials

Read `.env` from workspace root:
- `HOSTPWD` → password for `OpenClawPI`
- `HOSTPWD2` → password for `OpenClawPI2`

If no parameters provided, ask: **"Back up which host? (OpenClawPI / OpenClawPI2)"**

Generate timestamp label from remote:
```bash
plink -pw "PASS" -batch stas@HOST "date +%Y%m%d_%H%M%S"
```
Local snapshot name: `taris_backup_HOST_vVERSION_TIMESTAMP`

---

## Step 1 — type: `data` (⚠️ Always run before deploy)

```bash
# Create archive on Pi (excludes models, logs, __pycache__)
plink -pw "PASS" -batch stas@HOST \
  "tar czf /tmp/taris_data_TS.tar.gz -C /home/stas \
    --exclude='.taris/__pycache__' --exclude='.taris/*/__pycache__' \
    --exclude='.taris/*.onnx' --exclude='.taris/*.bin' --exclude='.taris/*.log' \
    .taris/taris.db .taris/*.json .taris/bot.env .taris/config.json \
    .taris/calendar/ .taris/mail_creds/ .taris/notes/ .taris/error_protocols/ \
    .taris/docs/ .taris/screens/ \
    2>/dev/null; echo done"

# Pull to local
pscp -pw "PASS" stas@HOST:/tmp/taris_data_TS.tar.gz "PATH\taris_backup_HOST_TS\"

# Cleanup
plink -pw "PASS" -batch stas@HOST "rm -f /tmp/taris_data_TS.tar.gz"
```

**Archive contents:** `taris.db`, `bot.env`, `config.json`, `voice_opts.json`, `calendar/`, `mail_creds/`, `notes/`, `docs/` (RAG uploaded documents), `screens/` (screen DSL YAML)

---

## Step 2 — type: `software`

```bash
plink -pw "PASS" -batch stas@HOST \
  "tar czf /tmp/taris_software_TS.tar.gz -C /home/stas \
    --exclude='.taris/*/__pycache__' \
    .taris/*.py .taris/strings.json .taris/release_notes.json \
    .taris/core/ .taris/security/ .taris/telegram/ \
    .taris/features/ .taris/ui/ .taris/web/ .taris/setup/ .taris/services/ \
    2>/dev/null; echo done"

pscp -pw "PASS" stas@HOST:/tmp/taris_software_TS.tar.gz "PATH\taris_backup_HOST_TS\"
plink -pw "PASS" -batch stas@HOST "rm -f /tmp/taris_software_TS.tar.gz"
```

---

## Step 3 — type: `system`

```bash
plink -pw "PASS" -batch stas@HOST \
  "tar czf /tmp/taris_system_TS.tar.gz \
    /etc/systemd/system/taris*.service /etc/systemd/system/taris*.timer \
    /etc/cron.d/ /etc/modprobe.d/ 2>/dev/null; echo done"

pscp -pw "PASS" stas@HOST:/tmp/taris_system_TS.tar.gz "PATH\taris_backup_HOST_TS\"
plink -pw "PASS" -batch stas@HOST "rm -f /tmp/taris_system_TS.tar.gz"

# Also capture crontab
plink -pw "PASS" -batch stas@HOST "crontab -l 2>/dev/null" \
  > "PATH\taris_backup_HOST_TS\crontab.txt"
```

---

## Step 4 — type: `binaries`

```bash
plink -pw "PASS" -batch stas@HOST \
  "pip3 freeze > /tmp/pip_freeze.txt 2>&1; \
   echo '---dpkg---' >> /tmp/pip_freeze.txt; \
   dpkg -l | grep -E 'python3|piper|vosk|ffmpeg|libopus|zram' >> /tmp/pip_freeze.txt 2>/dev/null"

pscp -pw "PASS" stas@HOST:/tmp/pip_freeze.txt \
  "PATH\taris_backup_HOST_TS\installed_packages.txt"
plink -pw "PASS" -batch stas@HOST "rm -f /tmp/pip_freeze.txt"
```

---

## Step 5 — Verify + report

```bash
# List backup directory
ls -lh "PATH\taris_backup_HOST_TS\"

# DB row counts (for data backup)
plink -pw "PASS" -batch stas@HOST \
  "python3 -c \"import sqlite3; c=sqlite3.connect('/home/stas/.taris/taris.db'); \
  [print(t,c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0]) \
  for t in ['users','calendar_events','notes_index','chat_history']]\""
```

Report:
```
✅ Backup complete
   Host    : HOST
   Type    : TYPE
   Path    : PATH\taris_backup_HOST_TS\
   Files   : <list .tar.gz + sizes>
```

---

## Rules

- **Never commit** backup archives — they contain secrets (`bot.env`, IMAP passwords).
- `backup/snapshots/` is git-ignored.
- Models (`.onnx`, `.bin`) are excluded — large (66–142 MB), re-downloadable via `setup_voice.sh`.
- Always do `type=data` before any migration or deploy.
- Keep last 3 local archives; delete older ones after confirmed successful deploy.
