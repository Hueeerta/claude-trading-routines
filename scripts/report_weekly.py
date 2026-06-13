"""Review semanal (domingo 18:00). Compara las métricas del paper trading contra
lo esperado por el backtest de la estrategia activa y detecta degradación.

Claude PROPONE ajustes; NO los aplica sin aprobación explícita del usuario.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradebot import backtester, data, ledger, metrics  # noqa: E402
from tradebot.config import settings, strategy_params  # noqa: E402
from tradebot.strategies.base import get_strategy  # noqa: E402


def _backtest_esperado(strategy_name: str) -> dict:
    s = settings()
    params = strategy_params(strategy_name)
    dl_years = s["historico"]["anios"] + s["historico"].get("warmup_anios", 1)
    tfs = get_strategy(strategy_name, params).frames_needed()
    all_trades = []
    for sym in s["symbols"]:
        frames = data.load_frames(sym, tfs, dl_years)
        res = backtester.run(get_strategy(strategy_name, params), frames,
                             capital=s["capital_inicial_usdt"],
                             risk_pct=s["riesgo_por_trade"], comision=s["comision"],
                             slippage=s["slippage"], symbol=sym)
        all_trades.extend(res["trades"])
    return metrics.from_trades(all_trades)


def main() -> None:
    s = settings()
    desde = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    closed = ledger.closed_trades()
    semana = [t for t in closed if t["closed_ts"] >= desde]

    paper_total = metrics.from_trades(closed)
    paper_semana = metrics.from_trades(semana)
    esperado = _backtest_esperado(s["estrategia_activa"])

    print(json.dumps({
        "estrategia": s["estrategia_activa"],
        "paper_semana": paper_semana,
        "paper_acumulado": paper_total,
        "backtest_esperado": esperado,
        "drawdown": metrics.max_drawdown(ledger.equity_curve()),
        "nota": "Comparar paper vs backtest. Proponer ajustes solo con aprobación.",
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
