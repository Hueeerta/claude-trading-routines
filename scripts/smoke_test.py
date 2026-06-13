"""Smoke test de conectividad de EJECUCIÓN en Binance Spot Testnet.

Hace un roundtrip mínimo y reversible para verificar que executor + stop + ledger
funcionan de punta a punta. Útil tras cada reseteo (~mensual) de la testnet.

Requiere --confirm (ejecuta órdenes reales en testnet, dinero ficticio).
Por defecto limpia las entradas que escribe en el ledger (--keep para conservarlas).

Uso: python scripts/smoke_test.py --confirm
"""
from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradebot import executor, ledger  # noqa: E402
from tradebot.config import LEDGER_DIR  # noqa: E402

SYMBOL = "BTC/USDT"
NOTIONAL_USDT = 15.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true", help="ejecuta órdenes reales en testnet")
    ap.add_argument("--keep", action="store_true", help="no limpiar el ledger al final")
    args = ap.parse_args()
    if not args.confirm:
        print("Falta --confirm. No se ejecutó nada.")
        return

    ex = executor.client()
    price = ex.fetch_ticker(SYMBOL)["last"]
    amount = NOTIONAL_USDT / price
    print(f"Precio BTC: {price} | comprando ~{NOTIONAL_USDT} USDT ({amount:.6f} BTC)")

    buy = executor.market_buy(SYMBOL, amount)
    filled = buy.get("filled") or amount
    print(f"  Compra OK: filled={filled} BTC, status={buy.get('status')}")

    stop_price = price * 0.90  # 10% abajo: no se dispara
    stop = executor.place_stop(SYMBOL, filled, stop_price)
    print(f"  Stop colocado: id={stop.get('id')} @ {stop_price:.2f}")

    pid = "smoke_" + uuid.uuid4().hex[:6]
    ledger.record_open(pid, SYMBOL, "long", price, stop_price, filled,
                       NOTIONAL_USDT * 0.10, "smoke_test")
    print(f"  Ledger: OPEN registrado ({pid})")

    # Revertir para dejar la cuenta plana
    executor.cancel_all(SYMBOL)
    sell = executor.market_sell(SYMBOL, filled)
    exit_price = sell.get("average") or ex.fetch_ticker(SYMBOL)["last"]
    pnl = filled * (exit_price - price)
    ledger.record_close(pid, exit_price, pnl, "smoke_test_revert")
    print(f"  Venta OK + stop cancelado. Ledger: CLOSE registrado. PnL≈{pnl:.4f} USDT")

    if not args.keep:
        # Limpiar SOLO las líneas de este smoke test del ledger
        _purge_smoke(pid)
        print("  Ledger limpiado (entradas smoke eliminadas).")

    print("OK: roundtrip testnet completo.")


def _purge_smoke(pid: str) -> None:
    import json
    path = LEDGER_DIR / "trades.jsonl"
    if not path.exists():
        return
    lines = [l for l in path.read_text(encoding="utf-8").splitlines()
             if l.strip() and json.loads(l).get("position_id") != pid]
    path.write_text(("\n".join(lines) + "\n") if lines else "", encoding="utf-8")


if __name__ == "__main__":
    main()
