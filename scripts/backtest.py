"""Backtest de una estrategia sobre el histórico cacheado. Salida JSON compacta.

Uso:
  python scripts/backtest.py --strategy trend_ema
  python scripts/backtest.py --strategy breakout_donchian --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradebot import backtester, data, metrics  # noqa: E402
from tradebot.config import settings, strategy_params  # noqa: E402
from tradebot.strategies.base import get_strategy  # noqa: E402


def main() -> None:
    s = settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default=s["estrategia_activa"])
    ap.add_argument("--json", action="store_true", help="solo JSON, sin resumen")
    args = ap.parse_args()

    params = strategy_params(args.strategy)
    years = s["historico"]["anios"]
    per_symbol = []
    all_trades = []

    for sym in s["symbols"]:
        df = data.load_or_download(sym, s["timeframe"], years)
        df_trend = data.load_or_download(sym, s["trend_timeframe"], years)
        strat = get_strategy(args.strategy, params)
        res = backtester.run(
            strat, df, df_trend,
            capital=s["capital_inicial_usdt"], risk_pct=s["riesgo_por_trade"],
            comision=s["comision"], slippage=s["slippage"], symbol=sym,
        )
        all_trades.extend(res.pop("trades"))
        per_symbol.append(res)

    combined = metrics.from_trades(all_trades)
    out = {
        "estrategia": args.strategy,
        "periodo_anios": years,
        "por_simbolo": per_symbol,
        "combinado": combined,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))

    if not args.json:
        print("\n--- Resumen ---", file=sys.stderr)
        for r in per_symbol:
            print(f"{r['symbol']}: {r['n_trades']} trades | retorno {r['retorno_pct']}% "
                  f"| PF {r['profit_factor']} | winrate {r['win_rate']} "
                  f"| maxDD {r['max_dd_pct']}%", file=sys.stderr)
        print(f"COMBINADO: {combined['n_trades']} trades | PF {combined['profit_factor']} "
              f"| expectancy {combined['expectancy_usdt']} USDT", file=sys.stderr)


if __name__ == "__main__":
    main()
