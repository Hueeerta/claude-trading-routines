"""Obtención de velas OHLCV desde la API pública de producción de Binance.

Importante: los datos vienen de PRODUCCIÓN (reales). Solo las órdenes van a la
testnet. El order book de la testnet es ilíquido y daría precios irreales.
"""
from __future__ import annotations

import time
from pathlib import Path

import ccxt
import pandas as pd

from .config import CACHE_DIR

_OHLCV_COLS = ["timestamp", "open", "high", "low", "close", "volume"]


def _exchange() -> ccxt.binance:
    """Cliente Binance público (sin keys), solo lectura de mercado."""
    return ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "spot"}})


def fetch_ohlcv(
    symbol: str,
    timeframe: str = "4h",
    limit: int = 500,
    since: int | None = None,
) -> pd.DataFrame:
    """Velas recientes. Devuelve DataFrame indexado por fecha UTC."""
    ex = _exchange()
    raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
    return _to_df(raw)


def fetch_history(symbol: str, timeframe: str, years: float) -> pd.DataFrame:
    """Descarga histórico paginado de los últimos `years` años."""
    ex = _exchange()
    ms_per_year = 365 * 24 * 60 * 60 * 1000
    since = ex.milliseconds() - int(years * ms_per_year)
    tf_ms = ex.parse_timeframe(timeframe) * 1000

    all_rows: list[list] = []
    cursor = since
    while True:
        batch = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=cursor, limit=1000)
        if not batch:
            break
        all_rows.extend(batch)
        cursor = batch[-1][0] + tf_ms
        if cursor >= ex.milliseconds() or len(batch) < 1000:
            break
        time.sleep(ex.rateLimit / 1000)

    df = _to_df(all_rows)
    return df[~df.index.duplicated(keep="first")]


def _to_df(raw: list[list]) -> pd.DataFrame:
    df = pd.DataFrame(raw, columns=_OHLCV_COLS)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df.set_index("timestamp").astype(float)


def _cache_path(symbol: str, timeframe: str, years: float) -> Path:
    safe = symbol.replace("/", "")
    return CACHE_DIR / f"{safe}_{timeframe}_{years:g}y.csv"


def load_or_download(symbol: str, timeframe: str, years: float) -> pd.DataFrame:
    """Lee del cache (keyed por años) si existe; si no, descarga y guarda."""
    CACHE_DIR.mkdir(exist_ok=True)
    path = _cache_path(symbol, timeframe, years)
    if path.exists():
        return pd.read_csv(path, index_col="timestamp", parse_dates=["timestamp"])
    df = fetch_history(symbol, timeframe, years)
    df.to_csv(path)
    return df


def load_frames(symbol: str, timeframes: list[str], years: float) -> dict[str, pd.DataFrame]:
    """Carga varios timeframes de un símbolo. `years` debe incluir el warmup de
    indicadores (ej. EMA200 diaria) además de la ventana de evaluación."""
    return {tf: load_or_download(symbol, tf, years) for tf in timeframes}
