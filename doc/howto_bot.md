# Pico Bot — User Guide

**@smartpico_bot** is a Telegram bot running on Raspberry Pi that provides AI chat, mail digest, system management, and voice interaction.

> **New users:** When you first send `/start`, your request is queued for admin approval. You will be notified once approved.

---

## Getting Started

1. Open the bot in Telegram and send `/start`.
2. The bot shows a welcome message and the main menu.
3. Tap a menu button to enter a mode. Press **🔙 Menu** at any time to go back.

---

## Menu Modes

### 📧 Mail Digest
Fetches and summarises your Gmail inbox for the **last 24 hours** using an AI model.

- Tap **📧 Почта / Mail Digest** from the main menu.
- The last generated digest is shown immediately.
- Tap **🔄 Refresh** to fetch a fresh digest right now.
- The daily digest also runs automatically at **19:00** every day.

---

### 💬 Chat (Free Chat)
Open-ended conversation with the AI. Ask anything — questions, explanations, translations, creative tasks.

- Type your message and send it.
- The AI replies in the same language you write in.
- Press `/menu` or tap **🔙 Menu** to exit.

---

### 🖥️ System Chat
Ask about the state of the Raspberry Pi in plain language. The bot translates your request into a shell command, shows it to you, and asks for confirmation before running.

**Example requests:**
- `show disk usage`
- `list running services`
- `CPU temperature`
- `last 20 lines of voice.log`
- `memory usage`
- `uptime`

> ⚠️ Only available for **Full** and **Admin** users (not guests).

---

### 🎤 Voice Session
Send a voice note directly to the bot — it transcribes your speech offline (Vosk), sends the text to the AI, and replies with both text and an audio response (Piper TTS).

**How to record:**
1. Tap **🎤 Voice Session** in the menu.
2. In the Telegram input bar, hold the **🎤 microphone** button to record.
3. Release to send the voice message.
4. The bot replies with text and a voice note.

> 🗣️ The voice model is Russian (`ru_RU-irina-medium`). Speak in Russian for best recognition.

---

### 🔐 Admin Panel
Full system management. Visible only to **Admin** users.

#### User Management
- **📋 Pending Requests** — list of users awaiting approval; badge shows pending count. Tap to **Approve** or **Block** each request.
- **👥 User List** — show all registered users and their status (approved / blocked).
- **➕ Add User** — grant a user access by entering their Telegram chat ID.
- **➖ Remove User** — revoke access by Telegram chat ID.

#### AI / LLM
- **🤖 Switch LLM** — Change the active language model:
  - OpenRouter (default) — 100+ models via free API
  - OpenAI ChatGPT — gpt-4o, gpt-4o-mini, o3-mini, o1, gpt-4.5-preview
  - YandexGPT *(planned)*
- OpenAI API key is entered once and stored persistently.

#### Voice Pipeline
- **⚡ Voice Opts** — toggle optional STT/TTS speed optimisations:

| Toggle | Effect | Time saving |
|--------|--------|-------------|
| Silence strip | Removes leading silence before STT | −6 s |
| 8 kHz sample rate | Lighter Vosk processing | −7 s |
| Warm Piper cache | Pre-loads TTS model at startup | −15 s cold start |
| Parallel TTS thread | Text reply appears immediately while TTS generates | text in ~3 s |
| Per-user audio toggle | Adds 🔇/🔊 button to every voice reply | skip TTS entirely |
| Piper model in RAM | Copies ONNX model to `/dev/shm` | −13 s TTS load |

#### System
- **📜 Changelog** — browse full version history with release notes.
- **🖥️ System Chat** — available from both admin and full-user menu.

> To find a user's chat ID, ask them to message [@userinfobot](https://t.me/userinfobot) on Telegram.

---

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Show welcome message and main menu |
| `/menu` | Open main menu |
| `/status` | Show current mode and service status |

---

## User Roles

| Role | Access |
|------|--------|
| 👑 **Admin** | All modes + full Admin panel (users, LLM, voice opts, changelog) |
| 👤 **Full** | Mail, Chat, System Chat, Voice |
| 👥 **Guest** | Mail, Chat, Voice |
| ⏳ **Pending** | Registration submitted, awaiting admin approval |
| 🚫 **Blocked** | Access denied by admin |

- **Admin** users are configured in `bot.env` (`ADMIN_USERS`).
- **Full** users are configured in `bot.env` (`ALLOWED_USERS`).
- **Guest** users are approved by an admin via the Pending Requests flow.
- When an unknown user sends `/start`, they enter **Pending** state automatically.

---

## User Registration Flow

1. New user sends `/start`.
2. Bot replies: *"Your registration request has been submitted. Please wait for admin approval."*
3. Admin receives a notification with **Approve** and **Block** buttons.
4. On approval: user is added as Guest and notified. On block: user receives a declined message.
5. The **📋 Pending Requests** button on the admin panel shows a live count of waiting requests.

---

## Language

The bot automatically detects your Telegram language setting:
- 🇷🇺 Russian Telegram → interface in **Russian**
- 🌐 Any other language → interface in **English**

---

## Voice Requirements

Voice recognition and speech synthesis run **fully offline** on the Pi — no cloud API needed.

| Component | Details |
|-----------|---------|
| STT | Vosk `vosk-model-small-ru` (48 MB, Russian only) |
| TTS | Piper `ru_RU-irina-medium` (66 MB, female voice) |
| Audio HAT | Joy-IT RB-TalkingPI (for standalone voice assistant) |

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| Bot doesn't respond | Service stopped | Admin: `sudo systemctl restart picoclaw-telegram` |
| Voice reply missing audio | Piper not installed | Run `setup_voice.sh` |
| Mail digest fails | Gmail credentials expired | Check IMAP App Password in `bot.env` |
| "Admins only" on System Chat | You are a guest user | Ask admin to upgrade your access |
| Voice not recognised | Spoke non-Russian | Use Russian (model is Russian-only) |
| Button press does nothing | Markdown parse error (fixed in v2026.3.16–17) | Update bot to latest version |
| Registration pending forever | Admin hasn't approved | Ask admin to check Pending Requests in admin panel |
| `/start` shows wrong menu | Role mismatch in `bot.env` | Check `ALLOWED_USERS` / `ADMIN_USERS` in `bot.env` |
