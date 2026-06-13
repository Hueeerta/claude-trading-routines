"""Carga de configuración (settings.yaml) y secretos (.env)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = ROOT / "config" / "settings.yaml"
LEDGER_DIR = ROOT / "ledger"
CACHE_DIR = ROOT / "data_cache"
DB_PATH = ROOT / "db" / "trades.db"

load_dotenv(ROOT / ".env")


@lru_cache(maxsize=1)
def settings() -> dict[str, Any]:
    """Devuelve el dict de settings.yaml (cacheado)."""
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def env(key: str, default: str | None = None, required: bool = False) -> str | None:
    """Lee una variable de entorno; si required y falta, lanza error claro."""
    val = os.getenv(key, default)
    if required and not val:
        raise RuntimeError(
            f"Falta la variable de entorno {key}. Complétala en .env (ver .env.example)."
        )
    return val


def strategy_params(name: str | None = None) -> dict[str, Any]:
    """Parámetros de una estrategia (por nombre o la activa)."""
    s = settings()
    name = name or s["estrategia_activa"]
    params = s.get("estrategias", {}).get(name)
    if params is None:
        raise KeyError(f"Estrategia '{name}' no definida en settings.yaml")
    return params
