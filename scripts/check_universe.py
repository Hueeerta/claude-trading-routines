"""Valida el universo configurado contra Binance (para la rutina mensual).

Verifica que cada par siga activo y reporta su volumen 24h en USDT, flagueando
deslistados o baja liquidez. NO edita settings.yaml: solo informa para que la
revisión proponga reemplazos con aprobación del usuario.

Uso: python scripts/check_universe.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import ccxt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradebot.config import settings  # noqa: E402

# Umbral de liquidez 24h. Calibrado para nuestro tamaño (~$400/posición): incluso
# unos pocos M$/día son de sobra. Solo marca mercados genuinamente delgados.
VOL_MIN_USDT = 5_000_000


def main() -> None:
    s = settings()
    ex = ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "spot"}})
    ex.load_markets()
    reporte = []
    for sym in s["symbols"]:
        activo = sym in ex.markets and ex.markets[sym].get("active", False)
        vol = None
        if activo:
            try:
                t = ex.fetch_ticker(sym)
                vol = t.get("quoteVolume")
            except Exception:
                activo = False
        flag = "OK"
        if not activo:
            flag = "DESLISTADO/INACTIVO"
        elif vol is not None and vol < VOL_MIN_USDT:
            flag = "BAJA_LIQUIDEZ"
        reporte.append({"symbol": sym, "activo": activo,
                        "vol_24h_usdt": round(vol) if vol else None, "flag": flag})
    alertas = [r for r in reporte if r["flag"] != "OK"]
    print(json.dumps({"universo": reporte, "alertas": alertas,
                      "accion": "Proponer reemplazo solo si hay alertas (con aprobación)."},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
