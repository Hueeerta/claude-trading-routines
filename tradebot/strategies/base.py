"""Interfaz común de estrategias. Una sola fuente de verdad: el mismo
`prepare()` se usa en backtest y en vivo.

Convención de salida de prepare(): el DataFrame 4h enriquecido con, al menos,
las columnas booleanas `long_entry`, `long_exit` y la columna `stop` (precio de
stop válido si se entra en esa vela). Spot long-only por ahora.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Signal:
    action: str | None  # 'long' o None
    entry: float | None
    stop: float | None
    reason: str


class Strategy:
    name: str = "base"

    def __init__(self, params: dict):
        self.p = params

    def prepare(self, df: pd.DataFrame, df_trend: pd.DataFrame) -> pd.DataFrame:
        """Devuelve df 4h con columnas long_entry, long_exit, stop. A implementar."""
        raise NotImplementedError

    def signal(self, df: pd.DataFrame, df_trend: pd.DataFrame) -> Signal:
        """Señal para la última vela CERRADA (uso en vivo)."""
        prepared = self.prepare(df, df_trend)
        last = prepared.iloc[-1]
        if bool(last["long_entry"]):
            return Signal("long", float(last["close"]), float(last["stop"]),
                          self._entry_reason(last))
        return Signal(None, None, None, self._flat_reason(last))

    # hooks de texto para mensajes (sobreescribibles)
    def _entry_reason(self, row) -> str:
        return f"Entrada {self.name}"

    def _flat_reason(self, row) -> str:
        return f"Sin entrada ({self.name})"


def align_trend(trend_series: pd.Series, index_4h: pd.DatetimeIndex) -> pd.Series:
    """Lleva una condición booleana diaria al índice 4h por forward-fill (sin
    lookahead: cada vela 4h ve el último cierre diario YA disponible). Devuelve
    bool; se castea a float internamente para evitar downcasting de pandas."""
    s = trend_series.astype(float)
    aligned = s.reindex(s.index.union(index_4h)).ffill().reindex(index_4h)
    return aligned.fillna(0.0) > 0.5


def get_strategy(name: str, params: dict) -> Strategy:
    from .trend_ema import TrendEMA
    from .breakout_donchian import BreakoutDonchian
    from .meanrev_bollinger import MeanRevBollinger

    registry = {
        "trend_ema": TrendEMA,
        "breakout_donchian": BreakoutDonchian,
        "meanrev_bollinger": MeanRevBollinger,
    }
    if name not in registry:
        raise KeyError(f"Estrategia desconocida: {name}")
    return registry[name](params)
