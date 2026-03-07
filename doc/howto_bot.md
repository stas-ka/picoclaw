# Pico Bot — User Guide

**@smartpico_bot** is a Telegram bot running on Raspberry Pi that provides AI chat, mail digest, system management, and voice interaction.

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
Manage guest user access. Visible only to **Admin** users.

- **Add user** — enter a Telegram chat ID to grant guest access (Mail, Chat, Voice).
- **User list** — show all current guest users.
- **Remove user** — revoke guest access by chat ID.

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
| 👑 **Admin** | All modes + Admin panel (add/remove users) |
| 👤 **Full** | Mail, Chat, System Chat, Voice |
| 👥 **Guest** | Mail, Chat, Voice |

Guest users are added by an admin via the Admin panel. Full users are configured in `bot.env` (`ALLOWED_USERS`). Admins are configured in `bot.env` (`ADMIN_USERS`).

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
