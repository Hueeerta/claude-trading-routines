"""Breakout: ruptura del máximo de N velas (Donchian) en 4h con confirmación
de volumen. Stop = canal medio. Salida cuando el precio cierra bajo el medio.
"""
from __future__ import annotations

import pandas as pd

from .. import indicators as ind
from .base import Strategy


class BreakoutDonchian(Strategy):
    name = "breakout_donchian"

    def prepare(self, df: pd.DataFrame, df_trend: pd.DataFrame) -> pd.DataFrame:
        p = self.p
        out = df.copy()
        dc = ind.donchian(out, p["canal"])
        # canal de velas PREVIAS (shift 1) para no incluir la vela actual (no lookahead)
        upper_prev = dc["dc_upper"].shift(1)
        out["dc_mid"] = dc["dc_mid"].shift(1)
        vol_sma = out["volume"].rolling(p["vol_periodo"]).mean()

        out["long_entry"] = (out["close"] > upper_prev) & (
            out["volume"] > p["vol_mult"] * vol_sma
        )
        out["long_exit"] = out["close"] < out["dc_mid"]
        out["stop"] = out["dc_mid"]
        return out

    def _entry_reason(self, row) -> str:
        return f"ruptura Donchian {self.p['canal']} con volumen >{self.p['vol_mult']}x media"
