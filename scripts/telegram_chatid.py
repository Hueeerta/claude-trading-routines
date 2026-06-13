"""Detecta tu chat_id de Telegram.

Pasos:
  1. Crea el bot con @BotFather y pon el token en .env (TELEGRAM_BOT_TOKEN).
  2. Envíale CUALQUIER mensaje a tu bot desde tu Telegram.
  3. Corre: python scripts/telegram_chatid.py
  4. Copia el chat_id que imprime a .env (TELEGRAM_CHAT_ID).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradebot import notify  # noqa: E402


def main() -> None:
    updates = notify.get_updates()
    if not updates:
        print("No hay mensajes. Envíale un mensaje a tu bot y reintenta.")
        return
    seen = {}
    for u in updates:
        msg = u.get("message") or u.get("channel_post") or {}
        chat = msg.get("chat", {})
        if chat.get("id") is not None:
            seen[chat["id"]] = chat.get("username") or chat.get("title") or chat.get("first_name")
    for cid, name in seen.items():
        print(f"chat_id={cid}  ({name})")


if __name__ == "__main__":
    main()
