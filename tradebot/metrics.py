"""Métricas de desempeño calculadas desde el ledger (deterministas)."""
from __future__ import annotations


def from_trades(closed: list[dict]) -> dict:
    """Win rate, profit factor, expectancy a partir de trades cerrados."""
    n = len(closed)
    if n == 0:
        return {"n_trades": 0, "win_rate": None, "profit_factor": None,
                "expectancy_usdt": None, "pnl_total_usdt": 0.0}
    pnls = [t["pnl_usdt"] for t in closed]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_win = sum(wins)
    gross_loss = -sum(losses)
    pf = (gross_win / gross_loss) if gross_loss > 0 else None
    return {
        "n_trades": n,
        "win_rate": round(len(wins) / n, 3),
        "profit_factor": round(pf, 2) if pf is not None else None,
        "expectancy_usdt": round(sum(pnls) / n, 2),
        "pnl_total_usdt": round(sum(pnls), 2),
    }


def max_drawdown(equity_curve: list[dict]) -> dict:
    """Máximo drawdown (%) y equity actual vs pico."""
    if not equity_curve:
        return {"max_dd_pct": None, "equity": None, "peak": None, "dd_actual_pct": 0.0}
    peak = equity_curve[0]["equity"]
    max_dd = 0.0
    for point in equity_curve:
        eq = point["equity"]
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)
    eq_now = equity_curve[-1]["equity"]
    dd_now = (peak - eq_now) / peak if peak > 0 else 0.0
    return {
        "max_dd_pct": round(max_dd * 100, 2),
        "dd_actual_pct": round(dd_now * 100, 2),
        "equity": round(eq_now, 2),
        "peak": round(peak, 2),
    }
