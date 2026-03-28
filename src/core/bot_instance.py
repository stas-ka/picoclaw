"""
bot_instance.py — Single shared Telegram bot instance.

Created once; imported by every module that needs to call the Telegram API.
Keeping the bot object here avoids circular imports between handler modules.
"""

import time
import logging
import telebot
from core.bot_config import BOT_TOKEN

log = logging.getLogger(__name__)


class _409Handler(telebot.ExceptionHandler):
    """Sleep 35 s on Telegram 409 Conflict (old long-poll still alive after restart)."""
    def handle(self, exc) -> bool:
        if isinstance(exc, telebot.apihelper.ApiTelegramException) and getattr(exc, "error_code", 0) == 409:
            log.warning("[Bot] 409 Conflict — old long-poll still alive; sleeping 35 s…")
            time.sleep(35)
            return True   # handled; telebot will retry
        return False      # not handled; telebot logs and retries normally


bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown", exception_handler=_409Handler())
