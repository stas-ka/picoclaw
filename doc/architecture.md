# Picoclaw Voice Assistant — Architecture

## Overview

A fully offline Russian voice interface running on a Raspberry Pi 3 B+. The pipeline converts spoken Russian into text, routes it to an LLM via picoclaw, then speaks the LLM response back in Russian — all locally except the LLM call.

```
Microphone (USB / I2S HAT)
      │
      ▼
 [pw-record]   ← PipeWire subprocess (S16_LE, 16 kHz, mono)
      │              fallback: parec (PulseAudio compat layer)
      ▼
 [Vosk STT]    ← vosk-model-small-ru-0.22 (48 MB, offline, Kaldi-based)
      │              streaming decode, 250 ms chunks
      ▼
 Hotword gate  ← fuzzy SequenceMatcher match on "пико / пика / пике / пик"
      │              threshold: 0.75 similarity ratio
      ▼
 [Vosk STT]    ← same model, fresh recognizer for the command phrase
      │              stops on 2 s silence or 15 s max
      ▼
 [picoclaw]    ← CLI subprocess: picoclaw agent -m "<text>"
      │              binary: /usr/bin/picoclaw (sipeed/picoclaw v0.2.0)
      ▼
 [OpenRouter]  ← HTTPS call to openrouter.ai (cloud, configurable model)
      │              default: openrouter/openai/gpt-4o-mini
      ▼
 [Piper TTS]   ← ru_RU-irina-medium.onnx (ONNX Runtime, 66 MB, offline)
      │              output: raw S16_LE PCM at 22050 Hz
      ▼
   [aplay]     ← ALSA playback → Pi 3.5 mm jack / USB speaker
```

---

## Component Details

### 1. Audio Capture — PipeWire / pw-record

| Property | Value |
|---|---|
| Backend | PipeWire (default on Raspberry Pi OS Bookworm) |
| Capture command | `pw-record --rate=16000 --channels=1 --format=s16 -` |
| Fallback | `parec --rate=16000 --channels=1 --format=s16le` |
| Chunk size | 4000 frames (250 ms at 16 kHz) |
| Required env vars | `XDG_RUNTIME_DIR=/run/user/1000`, `PIPEWIRE_RUNTIME_DIR=/run/user/1000`, `PULSE_SERVER=unix:/run/user/1000/pulse/native` |
| Source selection | Configurable via `AUDIO_TARGET` env var (see below) |

**`AUDIO_TARGET` values:**

| Value | Behavior |
|---|---|
| `auto` (default) | Let PipeWire select the default source |
| `webcam` | Use Philips SPC 520 USB webcam mic node |
| `<node name>` | Any PipeWire source node (from `pactl list sources short`) |

> **Known issue**: Philips SPC 520/525NC USB webcam mic fails on Pi 3's DWC_OTG USB controller — isochronous transfers complete the USB handshake but deliver zero data. `implicit_fb=1` modprobe flag does not resolve this. Use a standard USB microphone or the I2S RB-TalkingPI HAT instead.

---

### 2. Speech-to-Text — Vosk

| Property | Value |
|---|---|
| Library | `vosk` 0.3.45 (Python binding for Kaldi-based ASR) |
| Model | `vosk-model-small-ru-0.22` (48 MB) |
| Model path | `/home/stas/.picoclaw/vosk-model-small-ru/` |
| Language | Russian |
| Mode | Streaming (real-time chunk processing) |
| Word timestamps | Enabled (`SetWords(True)`) |
| CPU usage | ~40–60% on Pi 3 single core during recognition |

**Why not the full model?**  
`vosk-model-ru-0.42` (1.5 GB) runs out of RAM on Pi 3 (1 GB). The small model handles short voice commands well.

---

### 3. Hotword Detection

Implemented in `voice_assistant.py` using Python's `difflib.SequenceMatcher`:

```
text → split into words → fuzzy match each word against hotword list
```

- Hotwords: `пико`, `пика`, `пике`, `пик`, `привет пико`
- Threshold: `0.75` similarity ratio
- Also checks exact substring before fuzzy match
- Bigram matching for two-word hotwords ("привет пико")

The hotword loop runs `pw-record` continuously at 16 kHz. When triggered:
1. Hotword stream is killed
2. A beep plays (`/usr/share/sounds/alsa/Front_Left.wav`)
3. A fresh Vosk recognizer records the command phrase
4. Stream restarts after the response is spoken

---

### 4. LLM — picoclaw + OpenRouter

| Property | Value |
|---|---|
| Binary | `/usr/bin/picoclaw` (sipeed/picoclaw v0.2.0 aarch64 deb) |
| Invocation | `picoclaw agent -m "<recognized text>"` |
| LLM provider | OpenRouter (`openrouter.ai`) |
| Default model | `openrouter/openai/gpt-4o-mini` |
| Config file | `/home/stas/.picoclaw/config.json` |
| Timeout | 60 seconds |

picoclaw wraps the OpenRouter API call, manages the model config, and returns plain text response to stdout. The voice assistant captures that stdout and pipes it to TTS.

**config.json structure (minimal):**
```json
{
  "model_list": [
    {
      "model_name": "openrouter-auto",
      "model": "openrouter/openai/gpt-4o-mini",
      "api_key": "sk-or-..."
    }
  ],
  "agents": {
    "defaults": { "model": "openrouter-auto" }
  }
}
```

---

### 5. Text-to-Speech — Piper

| Property | Value |
|---|---|
| Engine | [Piper TTS](https://github.com/rhasspy/piper) (ONNX Runtime) |
| Binary | `/usr/local/bin/piper` (wrapper calling `/usr/local/share/piper/piper`) |
| Voice model | `ru_RU-irina-medium.onnx` (66 MB, natural female Russian) |
| Model path | `/home/stas/.picoclaw/ru_RU-irina-medium.onnx` |
| Output format | Raw PCM S16_LE at 22050 Hz mono |
| Playback | `aplay --rate=22050 --format=S16_LE --channels=1 -` |
| Latency | ~1–3 seconds per sentence on Pi 3 (RTF ≈ 0.83) |
| RAM usage | ~150 MB peak |

**Why Piper instead of Silero?**  
Silero TTS requires PyTorch (~2 GB download, ~1.5 GB RAM at runtime). Pi 3 has 1 GB RAM total — impossible. Piper uses ONNX Runtime with bundled shared libs, no Python dependencies, runs comfortably on Pi 3.

**Pipeline:**
```
echo "text" → piper stdin  →  piper stdout (raw PCM)  →  aplay stdin  →  speaker
```
Piper and aplay run as chained subprocesses with a pipe between them.

---

### 6. Telegram Gateway (parallel channel)

The picoclaw gateway also handles Telegram messages independently of the voice assistant:

| Property | Value |
|---|---|
| Bot | `@smartpico_bot` |
| Service | `picoclaw-gateway.service` (systemd) |
| LLM | Same OpenRouter config |
| Allowed user | Chat ID `994963580` |

---

### 7. Telegram Menu Bot (`telegram_menu_bot.py`)

Interactive Telegram bot (`BOT_VERSION = "2026.3.20"`) with mode switching, voice sessions, notes, admin panel, and internationalization (Russian / English).

#### User modes (inline keyboard)

| Mode | Button | Description |
|---|---|---|
| Mail Digest | 📧 Mail Digest | Runs `gmail_digest.py --stdout` and returns the summary inline |
| Free Chat | 💬 Free Chat | Any text sent goes directly to `picoclaw agent -m` and returns the LLM response |
| System Chat | 🖥 System Chat | Like Free Chat but prepends a system-admin context prompt |
| **Voice Session** | **🎤 Voice Session** | **On-demand mic session: see below** |
| **Notes** | **📝 Notes** | **Personal Markdown note manager: create, edit, view, delete, read aloud** |

#### Admin panel buttons

| Button | Action |
|---|---|
| ➕ Add user | Add a guest user by Telegram chat ID |
| 📋 List users | Show all authorised guest users |
| 🗑 Remove user | Remove a guest user |
| 🤖 Switch LLM | Switch active model (OpenRouter default + OpenAI sub-menu with gpt-4o, gpt-4o-mini, o3-mini, o1, gpt-4.5-preview) |
| ⚡ Voice Opts | Toggle 10 optional voice latency optimizations (see below) |
| 📝 Release Notes | Show full versioned changelog from `release_notes.json` |

| Property | Value |
|---|---|
| Script | `/home/stas/.picoclaw/telegram_menu_bot.py` |
| Service | `picoclaw-telegram.service` (systemd) |
| Bot | `@smartpico_bot` |
| Token source | `/home/stas/.picoclaw/bot.env` (loaded via `EnvironmentFile=`) |
| Allowed user | `ALLOWED_USER` env var (chat ID) |
| LLM backend | `picoclaw agent -m` subprocess (same config as gateway) |
| i18n | `strings.json` (Russian + English, `_t(chat_id, key)`) |
| Version constant | `BOT_VERSION = "2026.3.19"` (bumped per deployment) |

#### Voice Session Mode

Tap **🎤 Voice Session** to enter voice mode — the bot prompts you to send a voice message:

```
User taps 🎤 Voice Session
  → Bot sends instructions, enters "voice" mode
  → User presses 🎤 mic button in Telegram, records Russian speech, sends it
  → Bot receives OGG Opus voice note from Telegram
  → ffmpeg: pipe OGG → 16 kHz mono S16LE raw PCM
  → Vosk KaldiRecognizer (Russian): PCM → transcript text
  → picoclaw agent -m "transcript"
  → LLM text response displayed with 🤖 header
  → Piper TTS → ffmpeg PCM→OGG Opus → bot.send_voice() voice note
```

**Note:** Voice messages sent via Telegram's mic button are processed automatically in *any* mode — no need to tap the Voice Session button first.

| Property | Value |
|---|---|
| Trigger | 🎤 mic button in Telegram input bar (standard Telegram feature) |
| Audio format received | OGG Opus (Telegram default) |
| Decode | `ffmpeg -i pipe:0 -ar 16000 -ac 1 -f s16le pipe:1` |
| STT | Vosk `vosk-model-small-ru` (Russian, offline) |
| TTS binary | `/usr/local/bin/piper` |
| TTS model | `~/.picoclaw/ru_RU-irina-medium.onnx` |
| Audio encoding | `ffmpeg` PCM S16LE 22050 Hz → OGG Opus 24 kbit/s |
| Delivery | Telegram `send_voice()` (OGG Opus) |

**Why not capture from Pi mic?** The Pi's USB microphone is exclusively locked by `picoclaw-voice.service` (always-on wake word detection). ALSA does not allow two processes to capture simultaneously. The Telegram bot instead uses the user's phone microphone via Telegram's native voice message feature.

**Relationship to the gateway:**  
`picoclaw-gateway.service` handles Telegram natively via the picoclaw Go binary (currently with `"enabled": false` in config.json — disabled in favour of the menu bot). `picoclaw-telegram.service` runs the menu bot independently and gives a structured, button-driven UX instead of raw chat.

#### Voice Optimization Flags (`⚡ Voice Opts`)

Ten optional flags persisted in `~/.picoclaw/voice_opts.json` (all `false` by default). Toggled per-admin in the admin panel.

| Flag | Default | Effect |
|---|---|---|
| `silence_strip` | off | Run `ffmpeg silenceremove` filter on incoming voice before Vosk decoding |
| `low_sample_rate` | off | Decode voice at 8 kHz instead of 16 kHz (faster Vosk, lower quality) |
| `warm_piper` | off | Pre-load Piper ONNX model into memory at startup (eliminates first-TTS cold-start) |
| `parallel_tts` | off | Start TTS synthesis in background thread immediately after LLM token streaming completes |
| `user_audio_toggle` | off | Enable per-user 🔊/🔇 audio reply toggle (user can opt out of TTS voice reply) |
| `tmpfs_model` | off | Copy Piper ONNX model to `/dev/shm` (RAM disk) for fastest possible model load |
| `vad_prefilter` | off | Apply WebRTC VAD noise gate to strip non-speech frames before Vosk STT |
| `whisper_stt` | off | Use `whisper.cpp` tiny model instead of Vosk for STT (requires binary + `ggml-tiny.bin`) |
| `piper_low_model` | off | Use `ru_RU-irina-low.onnx` instead of medium quality (faster TTS, lower quality) |
| `persistent_piper` | off | Keep a long-running Piper subprocess alive to hold ONNX in page cache between calls |

Settings file: `~/.picoclaw/voice_opts.json`  

#### Release Notes & Deployment Tracking

The bot tracks its own version and notifies admins exactly once per version bump on startup.

| Item | Value |
|---|---|
| Constant | `BOT_VERSION = "2026.3.20"` in `telegram_menu_bot.py` |
| Changelog source | `release_notes.json` (deployed alongside bot script) |
| Tracking file | `~/.picoclaw/last_notified_version.txt` (auto-created; stores last notified version) |
| Trigger | On bot startup: if `BOT_VERSION != last_notified`, send changelog entry to all admins via Telegram |
| Admin access | Admin panel → 📝 Release Notes shows full changelog |

**Deployment workflow:** bump `BOT_VERSION`, add entry to top of `release_notes.json`, deploy both files + restart service. Admins receive notification automatically.

---

### 8. Gmail Digest Agent (cron job)

Daily email digest sent to Telegram at 19:00 Pi local time:

| Property | Value |
|---|---|
| Script | `/home/stas/.picoclaw/gmail_digest.py` |
| Cron | `0 19 * * *` |
| IMAP | `stas.ulmer@gmail.com` via App Password |
| Folders | INBOX + `[Google Mail]/Spam` (last 24 h, max 50 each) |
| Output | Telegram `@smartpico_bot` → chat `994963580` |

---

## Process Hierarchy (at runtime)

```
systemd
  ├── picoclaw-gateway.service
  │     └── /usr/bin/picoclaw gateway
  │
  ├── picoclaw-telegram.service
  │     └── /usr/bin/python3 telegram_menu_bot.py
  │           ├── /usr/bin/picoclaw agent -m "..." [subprocess, per message]
  │           ├── /usr/bin/python3 gmail_digest.py --stdout [subprocess, on demand]
  │           └── [voice handler thread, per received voice note]
  │                 ├── ffmpeg -i pipe:0 ... [subprocess] ← OGG → PCM decode
  │                 ├── /usr/local/bin/piper [subprocess] ← TTS synthesis
  │                 └── ffmpeg ... pipe:1 [subprocess] ← PCM → OGG Opus encode
  │
  └── picoclaw-voice.service
        └── /usr/bin/python3 voice_assistant.py
              ├── pw-record [subprocess, stdout pipe] ← continuous hotword listen
              ├── pw-record [subprocess, stdout pipe] ← command recording (transient)
              ├── piper     [subprocess, stdin/stdout pipe] ← TTS synthesis
              └── aplay     [subprocess, stdin pipe]        ← audio output
```

---

## File Layout on Pi

```
/home/stas/.picoclaw/
  voice_assistant.py          ← main voice daemon
  telegram_menu_bot.py        ← interactive Telegram menu bot (v2026.3.19)
  bot_config.py               ← constants, env loading, logging
  bot_state.py                ← mutable runtime state dicts
  bot_instance.py             ← TeleBot singleton
  bot_access.py               ← access control, i18n, keyboards, LLM wrapper
  bot_users.py                ← registration + notes file I/O
  bot_voice.py                ← full voice pipeline: STT/TTS/VAD + note read-aloud
  bot_admin.py                ← admin panel: users, LLM, voice opts, release notes
  bot_handlers.py             ← user handlers: digest, chat, system, notes UI
  strings.json                ← i18n UI strings (ru/en), deployed alongside bot
  release_notes.json          ← versioned changelog, deployed alongside bot
  config.json                 ← picoclaw + LLM config (API key here)
  gmail_digest.py             ← daily email digest agent
  bot.env                     ← BOT_TOKEN + ALLOWED_USER (loaded by systemd EnvironmentFile=)
  voice_opts.json             ← voice optimization flags (auto-created; do not commit)
  last_notified_version.txt   ← tracks last BOT_VERSION admin notification (auto-created)
  pending_tts.json            ← TTS orphan-cleanup tracker (auto-created)
  users.json                  ← dynamically approved guest users (auto-created)
  registrations.json          ← user registration records: pending/approved/blocked (auto-created)
  notes/<chat_id>/<slug>.md   ← per-user Markdown note files (auto-created)
  vosk-model-small-ru/        ← 48 MB Vosk Russian STT model directory
  ru_RU-irina-medium.onnx     ← 66 MB Piper TTS voice model
  ru_RU-irina-medium.onnx.json← Piper voice metadata
  voice.log                   ← voice assistant log (append)
  digest.log                  ← Gmail digest log
  last_digest.txt             ← last digest output (read by menu bot)

/usr/local/bin/piper          ← Piper wrapper script
/usr/local/share/piper/       ← Piper binary + bundled libs (libonnxruntime, etc.)
  piper
  libpiper_phonemize.so.1
  libonnxruntime.so.1.14.1
  ...

/usr/bin/picoclaw             ← picoclaw Go binary (from .deb)
/usr/bin/picoclaw-launcher
/usr/bin/picoclaw-launcher-tui

/etc/systemd/system/
  picoclaw-gateway.service
  picoclaw-voice.service
  picoclaw-telegram.service

/mnt/ssd/backups/images/               ← full SD card image backups (optional, requires USB SSD)
  mico-image-rpi3-YYYY-MM-DD.img.zst   ← compressed image (zstd)
  mico-image-rpi3-YYYY-MM-DD.img.zst.sha256

/etc/modprobe.d/
  usb-audio-fix.conf          ← options snd-usb-audio implicit_fb=1
```

---

## Configuration Reference

### `telegram_menu_bot.py` constants

| Constant | Default | Env Override | Description |
|---|---|---|---|
| `BOT_VERSION` | `"2026.3.15-rc1"` | — | Version string; bump on every deployment |
| `RELEASE_NOTES_FILE` | `release_notes.json` next to script | `RELEASE_NOTES_FILE` | Path to versioned changelog JSON |
| `LAST_NOTIFIED_FILE` | `~/.picoclaw/last_notified_version.txt` | — | Tracks last admin-notified version |
| `_VOICE_OPTS_FILE` | `~/.picoclaw/voice_opts.json` | — | Persistent voice optimization flags |
| `PIPER_BIN` | `/usr/local/bin/piper` | `PIPER_BIN` | Piper TTS binary |
| `PIPER_MODEL` | `~/.picoclaw/ru_RU-irina-medium.onnx` | `PIPER_MODEL` | Piper voice model |
| `VOICE_SAMPLE_RATE` | `16000` | — | Base Vosk decode sample rate (Hz) |
| `TTS_MAX_CHARS` | `200` | — | Max characters per TTS chunk (prevents timeout) |
| `STRINGS_FILE` | `strings.json` next to script | `STRINGS_FILE` | i18n UI text file (ru/en) |
| `REGISTRATIONS_FILE` | `~/.picoclaw/registrations.json` | `REGISTRATIONS_FILE` | User registration records (pending/approved/blocked) |

### `voice_assistant.py` CONFIG

| Key | Default | Env Override | Description |
|---|---|---|---|
| `vosk_model_path` | `/home/stas/.picoclaw/vosk-model-small-ru` | `VOSK_MODEL_PATH` | Vosk model directory |
| `piper_bin` | `/usr/local/bin/piper` | `PIPER_BIN` | Piper TTS binary path |
| `piper_model` | `/home/stas/.picoclaw/ru_RU-irina-medium.onnx` | `PIPER_MODEL` | Piper voice model |
| `picoclaw_bin` | `/usr/bin/picoclaw` | `PICOCLAW_BIN` | picoclaw binary |
| `pipewire_runtime_dir` | `/run/user/1000` | — | PipeWire runtime socket dir |
| `audio_target` | `auto` | `AUDIO_TARGET` | Microphone selection |
| `sample_rate` | `16000` | — | Audio capture rate (Hz) |
| `chunk_size` | `4000` | — | Frames per processing chunk |
| `hotwords` | `["пико", "пика", ...]` | — | Wake words list |
| `hotword_threshold` | `0.75` | — | Fuzzy match sensitivity |
| `silence_timeout` | `2.0` | — | Seconds of silence to end recording |
| `max_phrase_duration` | `15.0` | — | Max command recording length (s) |
| `min_phrase_chars` | `3` | — | Minimum chars to accept STT result |

---

## Backup System (§6.3)

Three-tier backup strategy:

| Tier | Location | What | Scripts |
|---|---|---|---|
| Source | GitHub (`master`) | Code, configs, service files, docs | git push |
| Image | `/mnt/ssd/backups/images/` | Full SD card `.img.zst` | `src/setup/backup_image.sh` |
| Remote | Nextcloud `/MicoBackups/` | Images + recovery bundles | `src/setup/backup_nextcloud.sh` |

### Scripts

| Script | Purpose |
|---|---|
| `src/setup/backup_image.sh` | Full SD card image backup via `dd | zstd`; SHA-256 checksum; prints restore instructions |
| `src/setup/backup_nextcloud.sh` | Upload/download/list/prune backups on Nextcloud via WebDAV (curl); SHA-256 verify |
| `src/setup/install.sh` | Complete fresh-install bootstrap: apt packages, pip packages, picoclaw binary, Vosk model, Piper TTS, service units, cron |
| `src/setup/update.sh` | Incremental update: re-deploy bot files, sync changed service units, restart active services |

### Recovery / Installation Bundle (`deploy/`)

| File | Description |
|---|---|
| `deploy/packages.txt` | Project-essential apt packages (annotated) |
| `deploy/requirements.txt` | Python pip requirements |

### Configuration — Nextcloud keys in `bot.env`

| Key | Description |
|---|---|
| `NEXTCLOUD_URL` | Nextcloud base URL, e.g. `https://cloud.example.com` |
| `NEXTCLOUD_USER` | Nextcloud username |
| `NEXTCLOUD_PASS` | Nextcloud app password |
| `NEXTCLOUD_REMOTE` | WebDAV sub-path, default `/MicoBackups` |
