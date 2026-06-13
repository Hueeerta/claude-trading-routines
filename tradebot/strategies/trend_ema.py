"""Tendencia: cruce EMA 20/50 en 4h, solo a favor de la tendencia diaria
(precio sobre EMA200 en 1d), con filtro RSI para no comprar sobre-extendido.
Stop = entry - atr_mult * ATR. Salida por cruce inverso.
"""
from __future__ import annotations

import pandas as pd

from .. import indicators as ind
from .base import Strategy, align_higher


class TrendEMA(Strategy):
    name = "trend_ema"
    base_tf = "4h"
    aux_tfs = ("1d",)

    def prepare(self, frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
        p = self.p
        out = frames["4h"].copy()
        df_trend = frames["1d"]
        ema_f = ind.ema(out["close"], p["ema_rapida"])
        ema_s = ind.ema(out["close"], p["ema_lenta"])
        out["rsi"] = ind.rsi(out["close"], p["rsi_periodo"])
        out["atr"] = ind.atr(out, p["atr_periodo"])

        ema_trend_1d = ind.ema(df_trend["close"], p["ema_tendencia"])
        uptrend = align_higher(df_trend["close"] > ema_trend_1d, out.index)

        cross_up = (ema_f > ema_s) & (ema_f.shift(1) <= ema_s.shift(1))
        cross_dn = (ema_f < ema_s) & (ema_f.shift(1) >= ema_s.shift(1))

        out["long_entry"] = cross_up & uptrend & (out["rsi"] < p["rsi_max_entrada"])
        out["long_exit"] = cross_dn
        out["stop"] = out["close"] - p["atr_mult_stop"] * out["atr"]
        return out

    def _entry_reason(self, row) -> str:
        return f"cruce EMA{self.p['ema_rapida']}/{self.p['ema_lenta']} alcista, tendencia 1d up, RSI {row['rsi']:.0f}"
