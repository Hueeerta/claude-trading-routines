"""Ciclo de trading (rutina). Pasos fijos:

  1) briefing (contexto desde el ledger)   2) datos frescos + señal por símbolo
  3) reconciliar posiciones (¿saltó algún stop entre ciclos?)
  4) trailing: mover el stop residente de las posiciones abiertas
  5) salidas por señal   6) entradas (con riesgo)   7) emitir JSON compacto

--dry-run: NO ejecuta órdenes ni escribe ledger; solo muestra el plan.

La estrategia decide; este script aplica reglas + riesgo. Claude interpreta el
JSON y redacta el mensaje de Telegram (no inventa señales).
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradebot import briefing, data, ledger, risk  # noqa: E402
from tradebot.config import settings  # noqa: E402
from tradebot.strategies.base import get_strategy  # noqa: E402

LIMIT_POR_TF = {"1h": 800, "4h": 400, "1d": 400, "1w": 300}
DUST_FRAC = 0.10  # si queda <10% del tamaño en el exchange, la posición se cerró


def _equity_and_cash(open_pos, prices, capital0):
    closed_pnl = sum(t["pnl_usdt"] for t in ledger.closed_trades())
    tied = sum(p["size"] * p["entry"] for p in open_pos)
    cash = capital0 + closed_pnl - tied
    open_value = sum(p["size"] * prices.get(p["symbol"], p["entry"]) for p in open_pos)
    return cash + open_value, cash


def _trailing_stop(prep, opened_ts, cur_stop, trail_mult):
    """Nuevo stop chandelier = max_high_desde_entrada - trail_mult*ATR. Solo sube."""
    if trail_mult <= 0 or "atr" not in prep.columns:
        return cur_stop, False
    bars = prep.loc[opened_ts:]
    if bars.empty:
        return cur_stop, False
    max_high = float(bars["high"].max())
    atr_now = float(prep["atr"].iloc[-1])
    if atr_now != atr_now:  # NaN
        return cur_stop, False
    cand = max_high - trail_mult * atr_now
    new = max(cur_stop, cand)
    return new, new > cur_stop * 1.001


def main() -> None:
    s = settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dry = args.dry_run

    brief = briefing.build(include_feeds=True)
    strat = get_strategy(s["estrategia_activa"], brief["params"])
    trail_mult = getattr(strat, "exit_cfg", {}).get("trail_mult", 0.0)

    open_pos = ledger.open_positions()
    prices: dict[str, float] = {}
    signals: dict[str, dict] = {}
    prep_by_sym: dict[str, object] = {}

    for sym in s["symbols"]:
        frames = {tf: data.fetch_ohlcv(sym, tf, limit=LIMIT_POR_TF.get(tf, 400))
                  for tf in strat.frames_needed()}
        prep = strat.prepare(frames)
        prep_by_sym[sym] = prep
        last = prep.iloc[-1]
        prices[sym] = float(last["close"])
        signals[sym] = {
            "close": float(last["close"]),
            "long_entry": bool(last["long_entry"]),
            "long_exit": bool(last["long_exit"]),
            "stop": (None if last["stop"] != last["stop"] else float(last["stop"])),
            "regla": strat._entry_reason(last) if bool(last["long_entry"]) else None,
        }

    acciones: list[dict] = []
    exec_mod = None
    balance = {}
    if not dry:
        from tradebot import executor as exec_mod  # noqa: F811
        balance = exec_mod.balance()

    # 3) reconciliar: ¿saltó el stop residente entre ciclos?
    vivas = []
    for p in open_pos:
        eff_stop = ledger.current_stop(p["position_id"]) or p["stop"]
        cerrada = False
        if not dry:
            base = p["symbol"].split("/")[0]
            held = balance.get(base, 0.0)
            if held < DUST_FRAC * p["size"]:
                cerrada = True
        if cerrada:
            pnl = p["size"] * (eff_stop - p["entry"])
            ledger.record_close(p["position_id"], eff_stop, pnl, "stop_residente")
            acciones.append({"tipo": "STOP_EJECUTADO", "symbol": p["symbol"],
                             "position_id": p["position_id"], "exit": round(eff_stop, 6),
                             "pnl_usdt": round(pnl, 2)})
        else:
            vivas.append(p)
    open_pos = vivas

    equity, cash = _equity_and_cash(open_pos, prices, s["capital_inicial_usdt"])
    cb = brief["circuit_breaker_activo"]

    # 4) trailing + 5) salidas por señal
    for p in open_pos:
        sym = p["symbol"]
        sig = signals.get(sym, {})
        if sig.get("long_exit"):
            exit_price = prices[sym]
            pnl = p["size"] * (exit_price - p["entry"])
            acciones.append({"tipo": "CERRAR", "symbol": sym,
                             "position_id": p["position_id"], "exit": exit_price,
                             "pnl_usdt": round(pnl, 2), "motivo": "salida_senal"})
            if not dry:
                exec_mod.cancel_all(sym)
                exec_mod.market_sell(sym, p["size"])
                ledger.record_close(p["position_id"], exit_price, pnl, "salida_senal")
            continue

        cur_stop = ledger.current_stop(p["position_id"]) or p["stop"]
        new_stop, moved = _trailing_stop(prep_by_sym[sym], p["opened_ts"],
                                         cur_stop, trail_mult)
        if moved:
            acciones.append({"tipo": "MOVER_STOP", "symbol": sym,
                             "position_id": p["position_id"],
                             "stop_anterior": round(cur_stop, 6),
                             "stop_nuevo": round(new_stop, 6)})
            if not dry:
                exec_mod.cancel_all(sym)
                exec_mod.place_stop(sym, p["size"], new_stop)
                ledger.record_stop(p["position_id"], round(new_stop, 6))

    # 6) entradas
    if cb:
        acciones.append({"tipo": "BLOQUEADO", "motivo": "circuit breaker (drawdown)"})
    else:
        for sym in s["symbols"]:
            sig = signals[sym]
            if not sig["long_entry"] or sig["stop"] is None:
                continue
            ok, motivo = risk.can_open(open_pos, sym, s["max_posiciones"], s["una_por_par"])
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
                pid = uuid.uuid4().hex[:8]
                exec_mod.market_buy(sym, sz.size)
                exec_mod.place_stop(sym, sz.size, sig["stop"])
                ledger.record_open(pid, sym, "long", sig["close"], sig["stop"],
                                   sz.size, sz.risk_usdt, strat.name)
                ledger.record_stop(pid, sig["stop"])
                cash -= sz.notional
                open_pos.append({"symbol": sym, "position_id": pid, "size": sz.size,
                                 "entry": sig["close"]})

    if not dry:
        ledger.record_equity(round(equity, 2), round(cash, 2))

    print(json.dumps({
        "dry_run": dry, "estrategia": s["estrategia_activa"],
        "equity_usdt": round(equity, 2), "circuit_breaker": cb,
        "regimen": brief.get("regimen"), "concepto_del_dia": brief["concepto_del_dia"],
        "posiciones_abiertas": len(open_pos), "senales": signals,
        "acciones": acciones, "metricas": brief["metricas"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
