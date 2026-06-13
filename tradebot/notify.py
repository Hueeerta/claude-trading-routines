"""Notificaciones a Telegram. Mensajes escuetos (economía de tokens y de ruido)."""
from __future__ import annotations

import requests

from .config import env, settings

_API = "https://api.telegram.org/bot{token}/{method}"


def _token() -> str:
    return env("TELEGRAM_BOT_TOKEN", required=True)


def send(text: str, chat_id: str | None = None) -> dict:
    """Envía un mensaje. Devuelve la respuesta de la API."""
    chat_id = chat_id or env("TELEGRAM_CHAT_ID", required=True)
    parse_mode = settings().get("telegram", {}).get("parse_mode", "HTML")
    r = requests.post(
        _API.format(token=_token(), method="sendMessage"),
        json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode,
              "disable_web_page_preview": True},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def get_updates() -> list[dict]:
    """Lee mensajes recientes al bot (para detectar el chat_id)."""
    r = requests.get(_API.format(token=_token(), method="getUpdates"), timeout=15)
    r.raise_for_status()
    return r.json().get("result", [])
