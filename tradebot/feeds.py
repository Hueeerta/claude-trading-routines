"""Feeds cuantitativos gratis (sin tokens de Claude).

Fear & Greed (alternative.me), funding rate (Binance futures público),
dominancia BTC y datos de mercado (CoinGecko). Todo tolerante a fallos:
si un feed cae, devuelve None en su campo y no rompe la rutina.
"""
from __future__ import annotations

from typing import Any

import requests

_TIMEOUT = 10


def _get(url: str, **kwargs) -> Any | None:
    try:
        r = requests.get(url, timeout=_TIMEOUT, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def fear_greed() -> dict | None:
    """Índice Fear & Greed de cripto (0-100)."""
    data = _get("https://api.alternative.me/fng/?limit=1")
    if not data or not data.get("data"):
        return None
    d = data["data"][0]
    return {"value": int(d["value"]), "label": d["value_classification"]}


def funding_rate(symbol: str = "BTCUSDT") -> float | None:
    """Último funding rate de perpetuos (señal de apalancamiento del mercado)."""
    data = _get(
        "https://fapi.binance.com/fapi/v1/fundingRate",
        params={"symbol": symbol, "limit": 1},
    )
    if not data:
        return None
    return float(data[0]["fundingRate"])


def btc_dominance() -> float | None:
    """Dominancia de BTC (% del market cap total)."""
    data = _get("https://api.coingecko.com/api/v3/global")
    if not data:
        return None
    return data["data"]["market_cap_percentage"].get("btc")


def snapshot(symbol: str = "BTCUSDT") -> dict:
    """Resumen compacto de régimen para el briefing. Campos None si falla el feed."""
    return {
        "fear_greed": fear_greed(),
        "funding": funding_rate(symbol),
        "btc_dominance": btc_dominance(),
    }
