"""Gestión de riesgo. No negociable: riesgo <= 2% por trade, stop obligatorio,
circuit breaker por drawdown. Mismas reglas en backtest y en vivo.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Sizing:
    size: float            # unidades del activo
    notional: float        # USDT desplegados
    risk_usdt: float       # pérdida si salta el stop
    pct_capital: float     # % del equity desplegado
    capped: bool           # True si se limitó por falta de cash


def position_size(equity: float, risk_pct: float, entry: float, stop: float,
                  cash_disponible: float | None = None) -> Sizing:
    """Tamaño tal que la pérdida al stop sea risk_pct del equity.

    size = (equity * risk_pct) / |entry - stop|
    En spot no se puede desplegar más que el cash disponible: se limita.
    """
    if entry <= 0 or stop <= 0 or entry == stop:
        raise ValueError("entry/stop inválidos para sizing")
    risk_usdt = equity * risk_pct
    per_unit = abs(entry - stop)
    size = risk_usdt / per_unit
    notional = size * entry
    capped = False

    limite = cash_disponible if cash_disponible is not None else equity
    if notional > limite:
        size = limite / entry
        notional = size * entry
        risk_usdt = size * per_unit  # el riesgo efectivo baja al limitar
        capped = True

    return Sizing(
        size=size, notional=notional, risk_usdt=risk_usdt,
        pct_capital=(notional / equity if equity > 0 else 0.0), capped=capped,
    )


def circuit_breaker(dd_actual_pct: float | None, umbral_pct: float) -> bool:
    """True si hay que dejar de abrir posiciones por drawdown."""
    return dd_actual_pct is not None and dd_actual_pct >= umbral_pct


def can_open(open_positions: list[dict], symbol: str, max_posiciones: int,
             una_por_par: bool) -> tuple[bool, str]:
    """¿Se puede abrir una posición en `symbol`?"""
    if len(open_positions) >= max_posiciones:
        return False, f"máximo de {max_posiciones} posiciones alcanzado"
    if una_por_par and any(p["symbol"] == symbol for p in open_positions):
        return False, f"ya hay posición abierta en {symbol}"
    return True, "ok"
