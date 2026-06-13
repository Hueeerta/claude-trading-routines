"""Reporte diario (rutina 21:30). JSON compacto: equity, posiciones, trades del
día, régimen y concepto del día. Claude lo narra escueto y, opcionalmente, agrega
2-3 titulares vía subagente Haiku (no en este script).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradebot import briefing, ledger  # noqa: E402


def main() -> None:
    hoy = datetime.now(timezone.utc).date().isoformat()
    brief = briefing.build(include_feeds=True)
    trades_hoy = [t for t in ledger.closed_trades() if t["closed_ts"][:10] == hoy]
    print(json.dumps({
        "fecha": hoy,
        "equity_usdt": brief["equity_usdt"],
        "drawdown": brief["drawdown"],
        "circuit_breaker": brief["circuit_breaker_activo"],
        "posiciones_abiertas": brief["posiciones_abiertas"],
        "trades_hoy": [{"symbol": t["symbol"], "pnl_usdt": round(t["pnl_usdt"], 2),
                        "reason": t["reason"]} for t in trades_hoy],
        "metricas_acumuladas": brief["metricas"],
        "regimen": brief.get("regimen"),
        "concepto_del_dia": brief["concepto_del_dia"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
