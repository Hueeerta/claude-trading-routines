"""Backtester event-driven, long-only spot. Reutiliza el `prepare()` de cada
estrategia (misma lógica que en vivo). Multi-timeframe: itera sobre el base_tf.

Sin lookahead:
  - señal de entrada en la vela i -> entra en el OPEN de i+1
  - señal de salida  en la vela i -> sale  en el OPEN de i+1
  - stop / take-profit / trailing: intrabar. El stop tiene prioridad (peor caso).

Gestión de salida soportada (según columnas que emita la estrategia):
  - 'long_exit'         -> salida total por señal
  - 'target'            -> take-profit único (sale todo)
  - 'tp1' + 'tp2'       -> scale-out: parcial en TP1, resto en TP2
  - exit_cfg de la estrategia: tp1_frac, breakeven_after_tp1, trail_mult
  - 'atr' (col)         -> requerido si trail_mult>0 (trailing tipo chandelier)

Aplica comisión y slippage. Una posición por símbolo a la vez; sizing al riesgo%.
Posiciones abiertas al final se cierran al último cierre ('fin_datos').
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import metrics, risk
from .strategies.base import Strategy

_DEFAULT_EXIT = {"tp1_frac": 1.0, "breakeven_after_tp1": False, "trail_mult": 0.0}


def run(strategy: Strategy, frames: dict[str, pd.DataFrame], *,
        capital: float, risk_pct: float, comision: float, slippage: float,
        symbol: str = "", start: str | None = None, end: str | None = None) -> dict:
    prep = strategy.prepare(frames)
    if start is not None or end is not None:
        prep = prep.loc[start:end]

    o = prep["open"].to_numpy()
    high = prep["high"].to_numpy()
    low = prep["low"].to_numpy()
    close = prep["close"].to_numpy()
    entry_sig = prep["long_entry"].fillna(False).to_numpy()
    exit_sig = prep["long_exit"].fillna(False).to_numpy()
    stop_arr = prep["stop"].to_numpy()

    def col(name):
        return prep[name].to_numpy() if name in prep.columns else None
    tp1_arr, tp2_arr, target_arr, atr_arr = (col("tp1"), col("tp2"),
                                             col("target"), col("atr"))

    cfg = {**_DEFAULT_EXIT, **getattr(strategy, "exit_cfg", {})}
    idx = prep.index

    equity = capital
    pos = None
    pending = None
    trades: list[dict] = []
    curve = [{"ts": idx[0].isoformat(), "equity": equity, "cash": equity}]
    pid = 0

    def book(p, qty, fill, leg):
        """Realiza una salida parcial/total de `qty` unidades a precio `fill`."""
        nonlocal equity
        pnl = qty * (fill - p["entry"]) - qty * fill * comision
        equity += pnl
        p["realized"] += pnl
        p["legs"].append(leg)
        p["remaining"] -= qty
        p["exit_px_acum"] += qty * fill
        p["exit_qty"] += qty

    def close_trade(p, ts):
        avg_exit = p["exit_px_acum"] / p["exit_qty"] if p["exit_qty"] else p["entry"]
        trades.append({
            "position_id": p["id"], "symbol": symbol, "side": "long",
            "strategy": strategy.name, "entry": p["entry"], "stop": p["init_stop"],
            "size": p["size_total"], "risk_usdt": p["risk_usdt"],
            "exit": avg_exit, "pnl_usdt": p["realized"],
            "reason": "+".join(dict.fromkeys(p["legs"])), "ts": p["opened_ts"],
            "closed_ts": ts,
        })

    n = len(prep)
    for i in range(n):
        ts = idx[i].isoformat()

        # 1) ejecutar pendiente en el OPEN
        if pending is not None and not np.isnan(o[i]):
            if pending[0] == "enter" and pos is None:
                entry_price = o[i] * (1 + slippage)
                stop = pending[1]
                if not np.isnan(stop) and entry_price > stop:
                    sz = risk.position_size(equity, risk_pct, entry_price, stop,
                                            cash_disponible=equity)
                    equity -= sz.notional * comision
                    pid += 1
                    pos = {"id": f"bt{pid}", "entry": entry_price, "init_stop": stop,
                           "stop": stop, "size_total": sz.size, "remaining": sz.size,
                           "risk_usdt": sz.risk_usdt, "tp1": pending[2],
                           "tp2": pending[3], "tp1_done": False, "hh": entry_price,
                           "realized": 0.0, "legs": [], "exit_px_acum": 0.0,
                           "exit_qty": 0.0, "opened_ts": ts}
            elif pending[0] == "exit" and pos is not None:
                book(pos, pos["remaining"], o[i] * (1 - slippage), "salida_senal")
                close_trade(pos, ts); pos = None
            pending = None

        # 2) gestión intrabar de la posición
        if pos is not None:
            pos["hh"] = max(pos["hh"], high[i])
            # trailing (solo sube el stop)
            if cfg["trail_mult"] > 0 and atr_arr is not None and not np.isnan(atr_arr[i]):
                pos["stop"] = max(pos["stop"], pos["hh"] - cfg["trail_mult"] * atr_arr[i])

            if not np.isnan(low[i]) and low[i] <= pos["stop"]:
                fill = min(o[i], pos["stop"]) * (1 - slippage)
                leg = "breakeven" if abs(pos["stop"] - pos["entry"]) < 1e-9 else (
                    "trailing" if pos["stop"] > pos["init_stop"] else "stop")
                book(pos, pos["remaining"], fill, leg)
                close_trade(pos, ts); pos = None

        if pos is not None:
            # TP1 parcial
            if (pos["tp1"] is not None and not pos["tp1_done"]
                    and not np.isnan(pos["tp1"]) and high[i] >= pos["tp1"]):
                qty = min(pos["size_total"] * cfg["tp1_frac"], pos["remaining"])
                book(pos, qty, max(o[i], pos["tp1"]) * (1 - slippage), "tp1")
                pos["tp1_done"] = True
                if cfg["breakeven_after_tp1"]:
                    pos["stop"] = max(pos["stop"], pos["entry"])
                if pos["remaining"] <= 1e-12:  # tp1_frac=1.0 -> salida total en TP1
                    close_trade(pos, ts); pos = None
            # TP2 / target (sale el resto)
            if pos is not None and pos["tp2"] is not None and not np.isnan(pos["tp2"]) \
                    and high[i] >= pos["tp2"] and pos["remaining"] > 0:
                book(pos, pos["remaining"], max(o[i], pos["tp2"]) * (1 - slippage), "tp2")
                close_trade(pos, ts); pos = None

        # 3) señales al cierre -> pendiente para la próxima vela
        if pos is None and entry_sig[i]:
            tp1 = tp1_arr[i] if tp1_arr is not None else None
            tp2 = tp2_arr[i] if tp2_arr is not None else (
                target_arr[i] if target_arr is not None else None)
            pending = ("enter", stop_arr[i], tp1, tp2)
        elif pos is not None and exit_sig[i]:
            pending = ("exit",)

        unreal = pos["remaining"] * (close[i] - pos["entry"]) if pos else 0.0
        curve.append({"ts": ts, "equity": round(equity + unreal, 2),
                      "cash": round(equity, 2)})

    # cerrar posición abierta al final
    if pos is not None:
        book(pos, pos["remaining"], close[-1] * (1 - slippage), "fin_datos")
        close_trade(pos, idx[-1].isoformat())

    m = metrics.from_trades(trades)
    m_dd = metrics.max_drawdown(curve)
    return {
        "symbol": symbol, "estrategia": strategy.name,
        "equity_final": round(equity, 2), "capital_inicial": capital,
        "retorno_pct": round((equity / capital - 1) * 100, 2),
        **m, "max_dd_pct": m_dd["max_dd_pct"], "trades": trades,
    }
