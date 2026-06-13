"""Ciclo de trading (rutina 4h). Pasos fijos:

  1) briefing (contexto desde el ledger)  2) datos frescos + señal por símbolo
  3) gestionar salidas de posiciones abiertas  4) gestionar entradas (con riesgo)
  5) emitir JSON compacto para que Claude lo narre.

--dry-run: NO ejecuta órdenes ni escribe en el ledger; solo muestra el plan.

La estrategia decide; este script solo aplica reglas + riesgo. Claude interpreta
el JSON y redacta el mensaje de Telegram (no inventa señales).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradebot import briefing, data, ledger, risk  # noqa: E402
from tradebot.config import settings  # noqa: E402
from tradebot.strategies.base import get_strategy  # noqa: E402


def _equity_and_cash(open_pos: list[dict], prices: dict[str, float], capital0: float) -> tuple[float, float]:
    closed_pnl = sum(t["pnl_usdt"] for t in ledger.closed_trades())
    tied = sum(p["size"] * p["entry"] for p in open_pos)
    cash = capital0 + closed_pnl - tied
    open_value = sum(p["size"] * prices.get(p["symbol"], p["entry"]) for p in open_pos)
    return cash + open_value, cash


def main() -> None:
    s = settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dry = args.dry_run

    brief = briefing.build(include_feeds=True)
    strat = get_strategy(s["estrategia_activa"], brief["params"])

    open_pos = ledger.open_positions()
    prices: dict[str, float] = {}
    signals: dict[str, dict] = {}

    for sym in s["symbols"]:
        df = data.fetch_ohlcv(sym, s["timeframe"], limit=400)
        df_trend = data.fetch_ohlcv(sym, s["trend_timeframe"], limit=400)
        prep = strat.prepare(df, df_trend)
        last = prep.iloc[-1]
        prices[sym] = float(last["close"])
        signals[sym] = {
            "close": float(last["close"]),
            "long_entry": bool(last["long_entry"]),
            "long_exit": bool(last["long_exit"]),
            "stop": (None if last["stop"] != last["stop"] else float(last["stop"])),
            "regla": strat._entry_reason(last) if bool(last["long_entry"]) else None,
        }

    equity, cash = _equity_and_cash(open_pos, prices, s["capital_inicial_usdt"])
    cb = brief["circuit_breaker_activo"]

    acciones: list[dict] = []

    # 3) salidas
    for p in open_pos:
        sig = signals.get(p["symbol"], {})
        if sig.get("long_exit"):
            exit_price = prices[p["symbol"]]
            pnl = p["size"] * (exit_price - p["entry"])
            acciones.append({"tipo": "CERRAR", "symbol": p["symbol"],
                             "position_id": p["position_id"], "exit": exit_price,
                             "pnl_usdt": round(pnl, 2), "motivo": "salida_senal"})
            if not dry:
                from tradebot import executor
                executor.cancel_all(p["symbol"])
                executor.market_sell(p["symbol"], p["size"])
                ledger.record_close(p["position_id"], exit_price, pnl, "salida_senal")

    # 4) entradas
    if cb:
        acciones.append({"tipo": "BLOQUEADO", "motivo": "circuit breaker (drawdown)"})
    else:
        abiertas_ahora = [p for p in open_pos
                          if p["position_id"] not in
                          {a.get("position_id") for a in acciones if a["tipo"] == "CERRAR"}]
        for sym in s["symbols"]:
            sig = signals[sym]
            if not sig["long_entry"] or sig["stop"] is None:
                continue
            ok, motivo = risk.can_open(abiertas_ahora, sym, s["max_posiciones"],
                                       s["una_por_par"])
            if not ok:
                acciones.append({"tipo": "SKIP", "symbol": sym, "motivo": motivo})
                continue
            sz = risk.position_size(equity, s["riesgo_por_trade"], sig["close"],
                                    sig["stop"], cash_disponible=cash)
            acciones.append({"tipo": "ABRIR", "symbol": sym, "entry": sig["close"],
                             "stop": sig["stop"], "size": round(sz.size, 8),
                             "risk_usdt": round(sz.risk_usdt, 2),
                             "pct_capital": round(sz.pct_capital * 100, 1),
                             "capped": sz.capped, "regla": sig["regla"]})
            if not dry:
                import uuid
                from tradebot import executor
                pid = uuid.uuid4().hex[:8]
                executor.market_buy(sym, sz.size)
                executor.place_stop(sym, sz.size, sig["stop"])
                ledger.record_open(pid, sym, "long", sig["close"], sig["stop"],
                                   sz.size, sz.risk_usdt, strat.name)
                cash -= sz.notional

    if not dry:
        ledger.record_equity(round(equity, 2), round(cash, 2))

    print(json.dumps({
        "dry_run": dry,
        "estrategia": s["estrategia_activa"],
        "equity_usdt": round(equity, 2),
        "circuit_breaker": cb,
        "regimen": brief.get("regimen"),
        "concepto_del_dia": brief["concepto_del_dia"],
        "senales": signals,
        "acciones": acciones,
        "metricas": brief["metricas"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
