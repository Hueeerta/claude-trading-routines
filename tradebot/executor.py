"""Ejecución de órdenes en Binance Spot Testnet (vía ccxt sandbox).

Solo testnet. Coloca entrada a mercado + stop protector (stop-loss-limit) que
queda residente en el exchange, así una posición no queda desprotegida entre
ciclos. La contabilidad real vive en el ledger, no en la testnet (se resetea).
"""
from __future__ import annotations

import ccxt

from .config import env

_client: ccxt.binance | None = None


def client() -> ccxt.binance:
    global _client
    if _client is None:
        ex = ccxt.binance({
            "apiKey": env("BINANCE_TESTNET_KEY", required=True),
            "secret": env("BINANCE_TESTNET_SECRET", required=True),
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })
        ex.set_sandbox_mode(True)  # -> testnet.binance.vision
        ex.load_markets()
        _client = ex
    return _client


def balance() -> dict:
    """Saldos no-cero de la cuenta testnet."""
    bal = client().fetch_balance()
    return {k: v for k, v in bal["total"].items() if v and v > 0}


def market_buy(symbol: str, amount: float) -> dict:
    ex = client()
    amt = float(ex.amount_to_precision(symbol, amount))
    return ex.create_order(symbol, "market", "buy", amt)


def market_sell(symbol: str, amount: float) -> dict:
    ex = client()
    amt = float(ex.amount_to_precision(symbol, amount))
    return ex.create_order(symbol, "market", "sell", amt)


def place_stop(symbol: str, amount: float, stop_price: float,
               limit_offset: float = 0.002) -> dict:
    """Stop-loss-limit de venta residente. limit ligeramente bajo el stop para
    asegurar ejecución."""
    ex = client()
    amt = float(ex.amount_to_precision(symbol, amount))
    stop = float(ex.price_to_precision(symbol, stop_price))
    limit = float(ex.price_to_precision(symbol, stop_price * (1 - limit_offset)))
    return ex.create_order(
        symbol, "STOP_LOSS_LIMIT", "sell", amt, limit,
        params={"stopPrice": stop},
    )


def cancel_all(symbol: str) -> None:
    ex = client()
    for o in ex.fetch_open_orders(symbol):
        ex.cancel_order(o["id"], symbol)


def min_notional(symbol: str) -> float:
    """Mínimo notional permitido por el mercado (para validar tamaño)."""
    m = client().market(symbol)
    return (m.get("limits", {}).get("cost", {}) or {}).get("min") or 0.0
