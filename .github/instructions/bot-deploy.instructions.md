---
applyTo: "src/telegram_menu_bot.py,src/bot_*.py,src/strings.json,src/release_notes.json,src/services/*.service"
---

# Bot Deploy — Skill

Use this skill whenever deploying bot changes to the Pi.

## Deployment Pipeline — MANDATORY ORDER

> **RULE: Engineering before Production — always.**
>
> 1. Deploy and test on **PI2** (`OpenClawPI2`) — engineering target.
> 2. **Only after** all tests pass and the change is committed and pushed to git:
> 3. Deploy to **PI1** (`OpenClawPI`) — production target.
>
> **NEVER** deploy directly to PI1 without prior validation on PI2.

## 1 — Version Bump

`BOT_VERSION = "YYYY.M.D"` in `src/core/bot_config.py` + prepend entry in `src/release_notes.json`. Never use `\_` in JSON. See `doc/quick-ref.md` §Version Bump.

## 2 — Deploy Files

```bat
rem Incremental — only changed files (use package subdirectory)
rem core/:     pscp -pw "%HOSTPWD%" src\core\<file>.py stas@<HOST>:/home/stas/.picoclaw/core/
rem security/: pscp -pw "%HOSTPWD%" src\security\<file>.py stas@<HOST>:/home/stas/.picoclaw/security/
rem telegram/: pscp -pw "%HOSTPWD%" src\telegram\<file>.py stas@<HOST>:/home/stas/.picoclaw/telegram/
rem features/: pscp -pw "%HOSTPWD%" src\features\<file>.py stas@<HOST>:/home/stas/.picoclaw/features/
rem ui/:       pscp -pw "%HOSTPWD%" src\ui\<file>.py stas@<HOST>:/home/stas/.picoclaw/ui/
rem root:      pscp -pw "%HOSTPWD%" src\telegram_menu_bot.py stas@<HOST>:/home/stas/.picoclaw/
pscp -pw "%HOSTPWD%" src\release_notes.json src\strings.json stas@OpenClawPI:/home/stas/.picoclaw/

rem Full deploy (all packages)
pscp -pw "%HOSTPWD%" src\core\*.py     stas@OpenClawPI:/home/stas/.picoclaw/core/
pscp -pw "%HOSTPWD%" src\security\*.py stas@OpenClawPI:/home/stas/.picoclaw/security/
pscp -pw "%HOSTPWD%" src\telegram\*.py stas@OpenClawPI:/home/stas/.picoclaw/telegram/
pscp -pw "%HOSTPWD%" src\features\*.py stas@OpenClawPI:/home/stas/.picoclaw/features/
pscp -pw "%HOSTPWD%" src\ui\*.py       stas@OpenClawPI:/home/stas/.picoclaw/ui/
pscp -pw "%HOSTPWD%" src\telegram_menu_bot.py src\bot_web.py stas@OpenClawPI:/home/stas/.picoclaw/
pscp -pw "%HOSTPWD%" src\release_notes.json src\strings.json stas@OpenClawPI:/home/stas/.picoclaw/
```

## 2a — First-Time Deploy (New Pi or After Restructure)

Before deploying Python files to a Pi that still has the flat (pre-package) layout, create
the package directories and `__init__.py` files first:

```bat
rem Create package directories on Pi
plink -pw "%HOSTPWD%" -batch stas@<HOST> "mkdir -p ~/.picoclaw/core ~/.picoclaw/security ~/.picoclaw/telegram ~/.picoclaw/features ~/.picoclaw/ui"
plink -pw "%HOSTPWD%" -batch stas@<HOST> "touch ~/.picoclaw/core/__init__.py ~/.picoclaw/security/__init__.py ~/.picoclaw/telegram/__init__.py ~/.picoclaw/features/__init__.py ~/.picoclaw/ui/__init__.py"

rem Then run full deploy (section 2)
```

## 3 — Restart and Verify

```bat
plink -pw "%HOSTPWD%" -batch stas@OpenClawPI "echo %HOSTPWD% | sudo -S systemctl restart picoclaw-telegram && sleep 3 && journalctl -u picoclaw-telegram -n 12 --no-pager"
```

Expected log: `[INFO] Version : 2026.X.Y` and `[INFO] Polling Telegram…`

## 4 — Service File Changes

When a `.service` file in `src/services/` changes, deploy it in the same operation:

```bat
pscp -pw "%HOSTPWD%" src\services\<name>.service stas@OpenClawPI:/tmp/<name>.service
plink -pw "%HOSTPWD%" -batch stas@OpenClawPI "echo %HOSTPWD% | sudo -S cp /tmp/<name>.service /etc/systemd/system/<name>.service && sudo systemctl daemon-reload && sudo systemctl restart <name>"
```

## 5 — UI Changes (Telegram + Web UI)

Any UI change must be deployed to both variants:

```bat
rem Telegram
pscp -pw "%HOSTPWD%" src\telegram_menu_bot.py src\strings.json stas@<HOST>:/home/stas/.picoclaw/
pscp -pw "%HOSTPWD%" src\telegram\bot_access.py stas@<HOST>:/home/stas/.picoclaw/telegram/

rem Web UI
pscp -pw "%HOSTPWD%" src\bot_web.py stas@<HOST>:/home/stas/.picoclaw/
pscp -pw "%HOSTPWD%" src\web\templates\*.html stas@<HOST>:/home/stas/.picoclaw/web/templates/
pscp -pw "%HOSTPWD%" src\web\static\style.css src\web\static\manifest.json stas@<HOST>:/home/stas/.picoclaw/web/static/

rem Restart both
plink -pw "%HOSTPWD%" -batch stas@<HOST> "echo %HOSTPWD% | sudo -S systemctl restart picoclaw-telegram picoclaw-web"
```

## picoclaw Binary (sipeed/picoclaw)

The Go AI agent binary at `/usr/bin/picoclaw` is a separate project from the bot.

```bat
rem Upgrade
plink -pw "%HOSTPWD%" -batch stas@OpenClawPI "wget -q https://github.com/sipeed/picoclaw/releases/latest/download/picoclaw_aarch64.deb -O /tmp/picoclaw_aarch64.deb && echo %HOSTPWD% | sudo -S dpkg -i /tmp/picoclaw_aarch64.deb"

rem One-shot chat
plink -pw "%HOSTPWD%" -batch stas@OpenClawPI "picoclaw agent -m \"Hello!\""
```

Config: `~/.picoclaw/config.json` — requires at least one `model_list` entry with an OpenRouter API key.

## Runtime Files (auto-created on Pi — do NOT commit)

Gmail digest: runs at 19:00 via cron; update with `pscp src\gmail_digest.py stas@<HOST>:/home/stas/.picoclaw/`



| File | Purpose |
|---|---|
| `~/.picoclaw/voice_opts.json` | Per-user voice flags |
| `~/.picoclaw/last_notified_version.txt` | Tracks notified `BOT_VERSION` |
| `~/.picoclaw/bot.env` | `BOT_TOKEN` + `ALLOWED_USER` (set manually) |
| `~/.picoclaw/pico.db` | SQLite data store |
