"""Ledger append-only en JSONL: fuente de verdad, versionada en Git.

Tres archivos:
  ledger/trades.jsonl  -> eventos OPEN y CLOSE (con position_id)
  ledger/equity.jsonl  -> snapshots de equity
  ledger/journal.jsonl -> notas / overlay de Claude

La testnet se resetea ~mensual, así que NO confiamos en ella para contabilidad:
el ledger es la verdad. SQLite se reconstruye desde aquí (rebuild_sqlite.py).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import LEDGER_DIR

TRADES = LEDGER_DIR / "trades.jsonl"
EQUITY = LEDGER_DIR / "equity.jsonl"
JOURNAL = LEDGER_DIR / "journal.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(path: Path, record: dict) -> None:
    LEDGER_DIR.mkdir(exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# ---- escritura ----

def record_open(position_id: str, symbol: str, side: str, entry: float, stop: float,
                size: float, risk_usdt: float, strategy: str, ts: str | None = None) -> None:
    _append(TRADES, {
        "event": "OPEN", "position_id": position_id, "ts": ts or _now(),
        "symbol": symbol, "side": side, "entry": entry, "stop": stop,
        "size": size, "risk_usdt": risk_usdt, "strategy": strategy,
    })


def record_close(position_id: str, exit_price: float, pnl_usdt: float,
                 reason: str, ts: str | None = None) -> None:
    _append(TRADES, {
        "event": "CLOSE", "position_id": position_id, "ts": ts or _now(),
        "exit": exit_price, "pnl_usdt": pnl_usdt, "reason": reason,
    })


def record_equity(equity: float, cash: float, ts: str | None = None) -> None:
    _append(EQUITY, {"ts": ts or _now(), "equity": equity, "cash": cash})


def record_journal(text: str, kind: str = "note", position_id: str | None = None,
                   ts: str | None = None) -> None:
    _append(JOURNAL, {"ts": ts or _now(), "kind": kind,
                      "position_id": position_id, "text": text})


# ---- vistas derivadas ----

def _trade_events() -> list[dict]:
    return _read(TRADES)


def open_positions() -> list[dict]:
    """Posiciones con OPEN sin CLOSE correspondiente."""
    opens: dict[str, dict] = {}
    for ev in _trade_events():
        pid = ev["position_id"]
        if ev["event"] == "OPEN":
            opens[pid] = ev
        elif ev["event"] == "CLOSE":
            opens.pop(pid, None)
    return list(opens.values())


def closed_trades() -> list[dict]:
    """Trades cerrados: fusiona OPEN+CLOSE por position_id."""
    opens: dict[str, dict] = {}
    closed: list[dict] = []
    for ev in _trade_events():
        pid = ev["position_id"]
        if ev["event"] == "OPEN":
            opens[pid] = ev
        elif ev["event"] == "CLOSE" and pid in opens:
            o = opens.pop(pid)
            closed.append({**o, **{k: ev[k] for k in ("exit", "pnl_usdt", "reason")},
                           "closed_ts": ev["ts"]})
    return closed


def latest_equity() -> dict | None:
    eq = _read(EQUITY)
    return eq[-1] if eq else None


def equity_curve() -> list[dict]:
    return _read(EQUITY)


def recent_closed(n: int = 5) -> list[dict]:
    return closed_trades()[-n:]


def recent_journal(n: int = 5) -> list[dict]:
    return _read(JOURNAL)[-n:]
