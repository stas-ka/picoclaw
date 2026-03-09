# Device Configuration Backup — OpenClawPI (PI1)
## Last updated: 2026-03-09

Raspberry Pi 3 **B+** Rev 1.3 running Raspberry Pi OS Bookworm (aarch64).  
Hostname: `OpenClawPI`, user: `stas`, CPU: 4× Cortex-A53 @ 1400 MHz, RAM: 905 MB.

---

## Files in this backup

| File | Source on Pi | Notes |
|---|---|---|
| `picoclaw-config.json` | `~/.picoclaw/config.json` | API keys replaced with `${VAR}` placeholders |
| `crontab` | `crontab -l` (user stas) | Gmail digest cron at 19:00 |
| `systemd/picoclaw-telegram.service` | `/etc/systemd/system/` | Telegram menu bot |
| `systemd/picoclaw-voice.service` | `/etc/systemd/system/` | Russian voice assistant (present but **disabled**) |
| `systemd/picoclaw-gateway.service` | `/etc/systemd/system/` | picoclaw LLM gateway (present, activating on boot but no active use) |
| `modprobe.d/usb-audio-fix.conf` | `/etc/modprobe.d/` | USB audio quirk fix |

---

## Installed software versions (2026-03-09)

| Component | Version |
|---|---|
| OS | Raspberry Pi OS Bookworm 64-bit |
| Kernel | 6.12.62+rpt-rpi-v8 |
| picoclaw (Go binary) | 0.2.0 |
| Python | **3.13.5** |
| vosk | 0.3.45 |
| webrtcvad-wheels | 2.0.14 |
| pyTelegramBotAPI | 4.31.0 |
| requests | 2.32.3 |
| requests-oauthlib | 2.0.0 |
| Piper TTS | 2023.11.14-2 (aarch64) |
| Piper voice | ru_RU-irina-medium (61 MB) |
| Vosk model | vosk-model-small-ru-0.22 (48 MB) |
| Whisper model | ggml-base.bin (142 MB), ggml-tiny.bin (75 MB) |
| whisper-cpp binary | /usr/local/bin/whisper-cpp |
| telegram_menu_bot.py | BOT_VERSION **2026.3.24** |

---

## Active voice optimization flags (voice_opts.json)

```json
{
  "silence_strip": false,
  "low_sample_rate": false,
  "warm_piper": true,
  "parallel_tts": false,
  "user_audio_toggle": false,
  "tmpfs_model": true,
  "vad_prefilter": false,
  "whisper_stt": true,
  "piper_low_model": false,
  "persistent_piper": false
}
```

---

## Runtime state files (auto-created, not in backup)

These files are created automatically by `telegram_menu_bot.py` at runtime.  
They are **not** committed to git and are not part of the backup snapshot.

| File | Description |
|---|---|
| `~/.picoclaw/voice_opts.json` | Per-user voice optimization flags (toggled in admin panel) |
| `~/.picoclaw/last_notified_version.txt` | Tracks last `BOT_VERSION` for which admins were notified |
| `~/.picoclaw/pending_tts.json` | TTS orphan-cleanup tracker (cleared on clean restart) |
| `~/.picoclaw/users.json` | Dynamically approved guest users (added via admin panel) |
| `~/.picoclaw/registrations.json` | User registration records: pending / approved / blocked |
| `~/.picoclaw/notes/<chat_id>/<slug>.md` | Per-user Markdown note files |

To reset voice opts: delete `~/.picoclaw/voice_opts.json` and restart the bot.
To re-trigger release notification: delete `~/.picoclaw/last_notified_version.txt` and restart.

---

## Active services (2026-03-09)

```
picoclaw-telegram.service  — enabled, active (running)
picoclaw-voice.service     — DISABLED, inactive  (deactivated 2026-03-09: no HAT connected, frees ~85 MB RAM)
picoclaw-gateway.service   — present, not enabled (activating state on boot, not in use)
```

---

## System settings (2026-03-09)

| Setting | Value | Notes |
|---|---|---|
| Boot target | `multi-user.target` | Desktop (lightdm) disabled |
| GPU memory | 76M | Recommendation: reduce to 16M (not yet applied) |
| CPU governor | `ondemand` | Recommendation: `performance` (not yet applied) |
| Swap | ~2.9 GB (swap partition) | No dphys-swapfile |
| Gmail crontab | `0 19 * * *` | Daily digest at 19:00 local time |

---

## boot config active entries (/boot/firmware/config.txt)

```
dtparam=audio=on
camera_auto_detect=1
display_auto_detect=1
auto_initramfs=1
dtoverlay=vc4-kms-v3d
max_framebuffers=2
disable_fw_kms_setup=1
arm_64bit=1
disable_overscan=1
arm_boost=1
```

Note: `dtparam=i2s=on` and RB-TalkingPI dtoverlay are **absent** — I2S HAT not connected.  
Enable in `/boot/firmware/config.txt` when attaching RB-TalkingPI HAT.

---

## Differences between PI1 and PI2

| Item | PI1 (OpenClawPI) | PI2 (OpenClawPI2) |
|---|---|---|
| Hardware | Pi 3 **B+** Rev 1.3 | Pi 3 **B** Rev 1.2 |
| CPU speed | 1400 MHz | 1200 MHz |
| Bot token | PI1-specific | PI2-specific (see .env) |
| Gmail crontab | Yes (`0 19 * * *`) | No |
| Swap | ~2.9 GB (partition) | ~905 MB (zram) |
| All other config | Identical | Identical |

---

## Restoring config on a new device

```bash
# 1. Restore bot service:
sudo cp systemd/picoclaw-telegram.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable picoclaw-telegram
sudo systemctl start  picoclaw-telegram

# 2. Restore crontab (PI1 only):
crontab crontab

# 3. Restore modprobe fix:
sudo cp modprobe.d/usb-audio-fix.conf /etc/modprobe.d/

# 4. Restore picoclaw config (fill in real API keys):
cp picoclaw-config.json ~/.picoclaw/config.json
# Edit: replace ${OPENROUTER_API_KEY} with real value

# 5. Ensure bot.env exists with BOT_TOKEN + ALLOWED_USERS + ADMIN_USERS
```
