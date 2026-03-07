# Backup Snapshot — 2026-03-07

**Host:** OpenClawPI (Raspberry Pi 3 B+, aarch64)  
**Bot version:** 2026.3.17  
**Created:** 2026-03-07 16:09–16:11 UTC+3  

---

## Contents

| File | Size | Description |
|---|---|---|
| `picoclaw-scripts-2026-03-07.tar.gz` | 121 KB | **Bundle A** — all scripts + configs, no binary models |
| `picoclaw-scripts-2026-03-07.tar.gz.sha256` | — | SHA-256 checksum for Bundle A |
| `picoclaw-full-2026-03-07.tar.gz` | 100 MB | **Bundle B** — full `~/.picoclaw/` incl. Vosk model + Piper ONNX |
| `picoclaw-full-2026-03-07.tar.gz.sha256` | — | SHA-256 checksum for Bundle B |
| `services-2026-03-07.tar.gz` | 1 KB | **Bundle C** — all `picoclaw-*.service` systemd unit files |
| `dpkg-selections-2026-03-07.txt` | 46 KB | Installed apt package list (`dpkg --get-selections`) |
| `pip-freeze-2026-03-07.txt` | 6 KB | Python pip packages (`pip3 freeze`), Python version, uname, crontab |

---

## What's included in Bundle A (scripts only)

`~/.picoclaw/` minus:
- `vosk-model-small-ru/` (48 MB Kaldi STT model)
- `*.onnx` (66 MB Piper TTS voice model)
- `*.log` files
- `pending_tts.json`, `last_notified_version.txt` (ephemeral runtime state)

Use Bundle A for quick config restores or diffing. Suitable for git archiving.

## What's included in Bundle B (full)

Everything in `~/.picoclaw/` except logs and ephemeral runtime files.  
Includes: Vosk model, Piper ONNX, all scripts, configs, credentials-free JSON files.

Use Bundle B for full disaster recovery to a fresh Pi.

---

## Restore procedure

### Restore scripts + configs only (Bundle A)
```bash
tar -xzf picoclaw-scripts-2026-03-07.tar.gz -C ~/.picoclaw/
sudo systemctl restart picoclaw-telegram
```

### Restore full install (Bundle B)
```bash
mkdir -p ~/.picoclaw
tar -xzf picoclaw-full-2026-03-07.tar.gz -C ~/.picoclaw/
# Restore service files
tar -xzf services-2026-03-07.tar.gz       # extracts picoclaw-*.service
sudo cp services/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable picoclaw-telegram picoclaw-gateway picoclaw-voice
sudo systemctl start  picoclaw-telegram picoclaw-gateway
# Restore crontab (from pip-freeze-2026-03-07.txt, see bottom of file)
# crontab -e   →  add:  0 19 * * * python3 ~/.picoclaw/gmail_digest.py >> ...
```

### Verify checksums before restore
```bash
sha256sum -c picoclaw-scripts-2026-03-07.tar.gz.sha256
sha256sum -c picoclaw-full-2026-03-07.tar.gz.sha256
```

---

## Notes

- `bot.env` (secrets file) is **not** included in any archive — restore from `.credentials/.pico_env`
- `gmail_credentials.json` and OAuth tokens included in Bundle B (these are non-secret app credentials)
- `registrations.json` + `users.json` included — contains Telegram user IDs
- After restore, run `picoclaw onboard` if `config.json` is missing or corrupt
