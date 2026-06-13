"""Backtester event-driven, long-only spot. Reutiliza el `prepare()` de cada
estrategia (misma lógica que en vivo). Sin lookahead:

  - señal de entrada en la vela i  -> se entra en el OPEN de la vela i+1
  - señal de salida  en la vela i  -> se sale  en el OPEN de la vela i+1
  - stop: se evalúa intrabar (low <= stop) y sale al precio de stop (o al open
    si hubo gap por debajo)

Aplica comisión y slippage. Una posición por símbolo a la vez; sizing al 2%.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import metrics, risk
from .strategies.base import Strategy


def run(strategy: Strategy, df: pd.DataFrame, df_trend: pd.DataFrame, *,
        capital: float, risk_pct: float, comision: float, slippage: float,
        symbol: str = "") -> dict:
    prep = strategy.prepare(df, df_trend)
    o = prep["open"].to_numpy()
    low = prep["low"].to_numpy()
    close = prep["close"].to_numpy()
    entry_sig = prep["long_entry"].fillna(False).to_numpy()
    exit_sig = prep["long_exit"].fillna(False).to_numpy()
    stop_arr = prep["stop"].to_numpy()
    idx = prep.index

    equity = capital
    pos = None  # dict(entry, stop, size)
    pending = None  # ('enter', stop) | ('exit',)
    trades: list[dict] = []
    curve: list[dict] = [{"ts": idx[0].isoformat(), "equity": equity, "cash": equity}]
    pid = 0

    n = len(prep)
    for i in range(n):
        ts = idx[i].isoformat()

        # 1) ejecutar orden pendiente en el OPEN de esta vela
        if pending is not None and not np.isnan(o[i]):
            if pending[0] == "enter" and pos is None:
                entry_price = o[i] * (1 + slippage)
                stop = pending[1]
                if not np.isnan(stop) and entry_price > stop:
                    sz = risk.position_size(equity, risk_pct, entry_price, stop,
                                            cash_disponible=equity)
                    equity -= sz.notional * comision  # comisión de compra
                    pid += 1
                    pos = {"id": f"bt{pid}", "entry": entry_price, "stop": stop,
                           "size": sz.size, "risk_usdt": sz.risk_usdt,
                           "opened_ts": ts}
            elif pending[0] == "exit" and pos is not None:
                _close(pos, o[i] * (1 - slippage), "salida_senal", ts, comision,
                       trades, symbol, strategy.name)
                equity += _pnl(pos, o[i] * (1 - slippage), comision)
                pos = None
            pending = None

        # 2) stop intrabar (si seguimos en posición)
        if pos is not None and not np.isnan(low[i]) and low[i] <= pos["stop"]:
            fill = min(o[i], pos["stop"]) * (1 - slippage)  # gap-aware
            equity += _pnl(pos, fill, comision)
            _close(pos, fill, "stop", ts, comision, trades, symbol, strategy.name)
            pos = None

        # 3) señales al cierre -> orden pendiente para la próxima vela
        if pos is None and entry_sig[i]:
            pending = ("enter", stop_arr[i])
        elif pos is not None and exit_sig[i]:
            pending = ("exit",)

        # marca de equity (valor a precio de cierre si hay posición)
        mark = equity + (pos["size"] * close[i] - pos["size"] * pos["entry"]
                         if pos else 0.0)
        curve.append({"ts": ts, "equity": round(mark, 2), "cash": round(equity, 2)})

    m = metrics.from_trades(trades)
    m_dd = metrics.max_drawdown(curve)
    return {
        "symbol": symbol, "estrategia": strategy.name,
        "equity_final": round(equity, 2), "capital_inicial": capital,
        "retorno_pct": round((equity / capital - 1) * 100, 2),
        **m, "max_dd_pct": m_dd["max_dd_pct"],
        "trades": trades,
    }


def _pnl(pos: dict, exit_price: float, comision: float) -> float:
    bruto = pos["size"] * (exit_price - pos["entry"])
    comision_venta = pos["size"] * exit_price * comision
    return bruto - comision_venta


def _close(pos, exit_price, reason, ts, comision, trades, symbol, strategy):
    trades.append({
        "position_id": pos["id"], "symbol": symbol, "side": "long",
        "strategy": strategy, "entry": pos["entry"], "stop": pos["stop"],
        "size": pos["size"], "risk_usdt": pos["risk_usdt"],
        "exit": exit_price, "pnl_usdt": _pnl(pos, exit_price, comision),
        "reason": reason, "ts": pos["opened_ts"], "closed_ts": ts,
    })
