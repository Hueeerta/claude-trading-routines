"""Indicadores técnicos implementados a mano (sin pandas-ta).

Todos toman/devuelven pandas Series/DataFrame y son deterministas.
"""
from __future__ import annotations

import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # Media de Wilder (EMA con alpha=1/period)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss
    out = 100 - (100 / (1 + rs))
    # avg_loss == 0 (sin pérdidas) => RSI 100; primeras filas sin datos => NaN
    out = out.where(avg_loss != 0, 100.0)
    return out


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range. df con columnas high/low/close."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def donchian(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Canal de Donchian: upper/lower/mid sobre `period` velas previas."""
    upper = df["high"].rolling(period).max()
    lower = df["low"].rolling(period).min()
    mid = (upper + lower) / 2
    return pd.DataFrame({"dc_upper": upper, "dc_lower": lower, "dc_mid": mid})


def bollinger(series: pd.Series, period: int = 20, dev: float = 2.0) -> pd.DataFrame:
    mid = series.rolling(period).mean()
    std = series.rolling(period).std(ddof=0)
    return pd.DataFrame(
        {"bb_mid": mid, "bb_upper": mid + dev * std, "bb_lower": mid - dev * std}
    )
