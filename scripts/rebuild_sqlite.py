"""Reconstruye db/trades.db desde el ledger JSONL (fuente de verdad).

SQLite es derivado y reconstruible -> ideal para el dashboard futuro y queries.
Uso: python scripts/rebuild_sqlite.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradebot import ledger  # noqa: E402
from tradebot.config import DB_PATH  # noqa: E402


def rebuild() -> dict:
    DB_PATH.parent.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE trades (
            position_id TEXT, symbol TEXT, side TEXT, strategy TEXT,
            entry REAL, stop REAL, size REAL, risk_usdt REAL,
            exit REAL, pnl_usdt REAL, reason TEXT, opened_ts TEXT, closed_ts TEXT
        );
        CREATE TABLE equity (ts TEXT, equity REAL, cash REAL);
        CREATE TABLE journal (ts TEXT, kind TEXT, position_id TEXT, text TEXT);
        """
    )
    closed = ledger.closed_trades()
    cur.executemany(
        "INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(t["position_id"], t["symbol"], t["side"], t["strategy"], t["entry"],
          t["stop"], t["size"], t["risk_usdt"], t["exit"], t["pnl_usdt"],
          t["reason"], t["ts"], t["closed_ts"]) for t in closed],
    )
    eq = ledger.equity_curve()
    cur.executemany("INSERT INTO equity VALUES (?,?,?)",
                    [(e["ts"], e["equity"], e["cash"]) for e in eq])
    jr = ledger.recent_journal(10**9)
    cur.executemany("INSERT INTO journal VALUES (?,?,?,?)",
                    [(j["ts"], j["kind"], j.get("position_id"), j["text"]) for j in jr])
    con.commit()
    con.close()
    return {"trades": len(closed), "equity_points": len(eq), "journal": len(jr)}


if __name__ == "__main__":
    print(rebuild())
