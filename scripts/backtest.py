"""Backtest de estrategias sobre el universo configurado. Multi-timeframe.

Calienta indicadores con `warmup_anios` extra y EVALÚA la ventana de `anios`.
Con --split divide la ventana en dos mitades (in-sample / out-of-sample) para
detectar sobre-optimización: una estrategia robusta rinde parecido en ambas.

Uso:
  python scripts/backtest.py --strategy mtf_ema_rsi
  python scripts/backtest.py --strategy all --split
  python scripts/backtest.py --strategy trend_ema --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradebot import backtester, data, metrics  # noqa: E402
from tradebot.config import settings, strategy_params  # noqa: E402
from tradebot.strategies.base import get_strategy  # noqa: E402

ALL = ["trend_ema", "breakout_donchian", "meanrev_bollinger", "mtf_ema_rsi"]


def _windows(anios: int, split: bool) -> dict[str, tuple[str | None, str | None]]:
    now = pd.Timestamp.utcnow()
    start = (now - pd.DateOffset(years=anios)).isoformat()
    if not split:
        return {"full": (start, None)}
    mid = (now - pd.DateOffset(years=anios) + pd.DateOffset(years=anios / 2)).isoformat()
    return {"in_sample": (start, mid), "out_sample": (mid, None)}


def run_strategy(name: str, anios: int, dl_years: float, windows: dict) -> dict:
    s = settings()
    params = strategy_params(name)
    strat0 = get_strategy(name, params)
    tfs = strat0.frames_needed()

    out: dict = {"estrategia": name, "ventanas": {}}
    for wname, (start, end) in windows.items():
        all_trades = []
        for sym in s["symbols"]:
            frames = data.load_frames(sym, tfs, dl_years)
            res = backtester.run(
                get_strategy(name, params), frames,
                capital=s["capital_inicial_usdt"], risk_pct=s["riesgo_por_trade"],
                comision=s["comision"], slippage=s["slippage"], symbol=sym,
                start=start, end=end,
            )
            all_trades.extend(res["trades"])
        out["ventanas"][wname] = metrics.from_trades(all_trades)
    return out


def main() -> None:
    s = settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default="all")
    ap.add_argument("--split", action="store_true", help="dividir en in/out-of-sample")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    anios = s["historico"]["anios"]
    dl_years = anios + s["historico"].get("warmup_anios", 1)
    windows = _windows(anios, args.split)
    names = ALL if args.strategy == "all" else [args.strategy]

    resultados = [run_strategy(n, anios, dl_years, windows) for n in names]
    print(json.dumps({"ventanas": list(windows.keys()), "resultados": resultados},
                     indent=2, ensure_ascii=False))

    if not args.json:
        print("\n--- Comparativo (PF / expectancy USDT / win / n) ---", file=sys.stderr)
        for r in resultados:
            line = [r["estrategia"].ljust(18)]
            for w, m in r["ventanas"].items():
                line.append(f"{w}: PF {m['profit_factor']} exp {m['expectancy_usdt']} "
                            f"win {m['win_rate']} n {m['n_trades']}")
            print(" | ".join(line), file=sys.stderr)


if __name__ == "__main__":
    main()
