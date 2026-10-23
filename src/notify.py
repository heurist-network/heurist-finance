"""Telegram delivery. Prints to stdout when no bot token is configured."""

from __future__ import annotations

import httpx

from src import config

TELEGRAM_LIMIT = 4096


def telegram(text: str) -> None:
    print(text)
    if not config.TELEGRAM_BOT_TOKEN:
        return
    for i in range(0, len(text), TELEGRAM_LIMIT):
        httpx.post(f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
                   json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[i:i + TELEGRAM_LIMIT]},
                   timeout=30).raise_for_status()
