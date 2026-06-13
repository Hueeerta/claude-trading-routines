"""Briefing: contexto compacto para el cold-start de cada rutina.

Cada rutina remota arranca sin memoria. Este módulo regenera desde el ledger
(la fuente de verdad) un JSON pequeño con todo lo necesario para analizar:
estrategia activa, equity, drawdown, posiciones, últimos trades, régimen y el
concepto del día. Objetivo: mínimo contexto, cero desperdicio de tokens.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from . import feeds, ledger, metrics
from .config import ROOT, settings, strategy_params

_CONCEPTS_PATH = ROOT / "education" / "concepts.md"


def _concepts() -> list[tuple[str, str]]:
    """Parsea concepts.md -> lista de (título, cuerpo)."""
    if not _CONCEPTS_PATH.exists():
        return []
    text = _CONCEPTS_PATH.read_text(encoding="utf-8")
    blocks = re.split(r"^### ", text, flags=re.MULTILINE)[1:]
    out = []
    for b in blocks:
        lines = b.strip().split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        out.append((title, body))
    return out


def concepto_del_dia() -> dict | None:
    """Rotación determinista por fecha (sin estado extra)."""
    cs = _concepts()
    if not cs:
        return None
    idx = date.today().toordinal() % len(cs)
    title, body = cs[idx]
    return {"titulo": title, "texto": body}


def build(include_feeds: bool = True) -> dict:
    """Construye el briefing compacto."""
    s = settings()
    estrategia = s["estrategia_activa"]
    closed = ledger.closed_trades()
    curve = ledger.equity_curve()
    dd = metrics.max_drawdown(curve)
    eq_now = dd["equity"] if dd["equity"] is not None else s["capital_inicial_usdt"]

    cb_umbral = s["drawdown_circuit_breaker"] * 100
    circuit_breaker = dd["dd_actual_pct"] is not None and dd["dd_actual_pct"] >= cb_umbral

    brief = {
        "estrategia": estrategia,
        "params": strategy_params(estrategia),
        "riesgo_por_trade": s["riesgo_por_trade"],
        "equity_usdt": round(eq_now, 2),
        "capital_inicial_usdt": s["capital_inicial_usdt"],
        "drawdown": dd,
        "circuit_breaker_activo": circuit_breaker,
        "posiciones_abiertas": [
            {k: p[k] for k in ("position_id", "symbol", "side", "entry", "stop", "size")}
            for p in ledger.open_positions()
        ],
        "metricas": metrics.from_trades(closed),
        "ultimos_trades": [
            {"symbol": t["symbol"], "pnl_usdt": round(t["pnl_usdt"], 2),
             "reason": t["reason"]}
            for t in ledger.recent_closed(5)
        ],
        "journal_reciente": [
            {"ts": j["ts"][:10], "kind": j["kind"], "text": j["text"]}
            for j in ledger.recent_journal(3)
        ],
        "concepto_del_dia": concepto_del_dia(),
    }
    if include_feeds:
        brief["regimen"] = feeds.snapshot("BTCUSDT")
    return brief
