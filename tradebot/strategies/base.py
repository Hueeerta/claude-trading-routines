"""Interfaz común de estrategias (multi-timeframe). Una sola fuente de verdad:
el mismo `prepare()` se usa en backtest y en vivo.

Cada estrategia declara:
  - base_tf: timeframe de ejecución/entrada (sobre el que itera el backtester)
  - aux_tfs: timeframes superiores usados como filtro (alineados al base por ffill)

prepare(frames) recibe un dict {tf: DataFrame OHLCV} y devuelve el DataFrame del
base_tf enriquecido con, al menos, las columnas:
  - long_entry (bool), long_exit (bool), stop (float)
  - opcional: target (float) take-profit; si está, el backtester sale al tocarlo.

Spot long-only.
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
    target: float | None = None


class Strategy:
    name: str = "base"
    base_tf: str = "4h"
    aux_tfs: tuple[str, ...] = ("1d",)

    def __init__(self, params: dict):
        self.p = params

    def frames_needed(self) -> list[str]:
        return [self.base_tf, *self.aux_tfs]

    def prepare(self, frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Devuelve el df del base_tf con long_entry, long_exit, stop[, target]."""
        raise NotImplementedError

    def signal(self, frames: dict[str, pd.DataFrame]) -> Signal:
        """Señal para la última vela CERRADA del base_tf (uso en vivo)."""
        prepared = self.prepare(frames)
        last = prepared.iloc[-1]
        if bool(last["long_entry"]):
            tgt = last.get("target")
            return Signal("long", float(last["close"]), float(last["stop"]),
                          self._entry_reason(last),
                          float(tgt) if tgt is not None and tgt == tgt else None)
        return Signal(None, None, None, self._flat_reason(last))

    def _entry_reason(self, row) -> str:
        return f"Entrada {self.name}"

    def _flat_reason(self, row) -> str:
        return f"Sin entrada ({self.name})"


def align_higher(condition: pd.Series, index_base: pd.DatetimeIndex) -> pd.Series:
    """Lleva una condición booleana de un timeframe superior al índice del base
    por forward-fill (sin lookahead: cada vela base ve el último cierre superior
    YA disponible). Devuelve bool."""
    s = condition.astype(float)
    aligned = s.reindex(s.index.union(index_base)).ffill().reindex(index_base)
    return aligned.fillna(0.0) > 0.5


def align_value(series: pd.Series, index_base: pd.DatetimeIndex) -> pd.Series:
    """Como align_higher pero para valores continuos (ej. ATR de 4H sobre 1H)."""
    return series.reindex(series.index.union(index_base)).ffill().reindex(index_base)


def get_strategy(name: str, params: dict) -> Strategy:
    from .trend_ema import TrendEMA
    from .breakout_donchian import BreakoutDonchian
    from .meanrev_bollinger import MeanRevBollinger
    from .mtf_ema_rsi import MTFEmaRsi

    registry = {
        "trend_ema": TrendEMA,
        "breakout_donchian": BreakoutDonchian,
        "meanrev_bollinger": MeanRevBollinger,
        "mtf_ema_rsi": MTFEmaRsi,
    }
    if name not in registry:
        raise KeyError(f"Estrategia desconocida: {name}")
    return registry[name](params)
