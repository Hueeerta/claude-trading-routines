"""Reversión a la media: toque de banda inferior de Bollinger + RSI bajo, solo
en mercado lateral (precio cerca de la EMA200 diaria). Target = media de Bollinger.
Stop = entry - atr_mult * ATR.
"""
from __future__ import annotations

import pandas as pd

from .. import indicators as ind
from .base import Strategy, align_trend


class MeanRevBollinger(Strategy):
    name = "meanrev_bollinger"

    def prepare(self, df: pd.DataFrame, df_trend: pd.DataFrame) -> pd.DataFrame:
        p = self.p
        out = df.copy()
        bb = ind.bollinger(out["close"], p["bb_periodo"], p["bb_desv"])
        out["bb_mid"] = bb["bb_mid"]
        out["rsi"] = ind.rsi(out["close"], p["rsi_periodo"])
        out["atr"] = ind.atr(out, p["atr_periodo"])

        ema_trend_1d = ind.ema(df_trend["close"], 200)
        desv_1d = (df_trend["close"] / ema_trend_1d - 1).abs()
        rango = align_trend(desv_1d < p["rango_max_desv"], out.index).fillna(False)

        out["long_entry"] = (
            (out["close"] < bb["bb_lower"]) & (out["rsi"] < p["rsi_max_entrada"]) & rango
        )
        out["long_exit"] = out["close"] >= out["bb_mid"]
        out["stop"] = out["close"] - p["atr_mult_stop"] * out["atr"]
        return out

    def _entry_reason(self, row) -> str:
        return f"toque banda inferior Bollinger, RSI {row['rsi']:.0f}, mercado en rango"
