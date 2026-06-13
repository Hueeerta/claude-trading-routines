"""Multi-timeframe EMA Trend + RSI Confirmation (portada del proyecto anterior).

Jerarquía 1W (sesgo) → 1D (estructura) → 4H (setup) → 1H (entrada).
ADAPTACIÓN A SPOT: solo-long (la lógica SHORT del original no es operable en spot).

LONG (requiere las 4 capas alineadas):
  1W : close > EMA20*(1+buffer)        → sesgo alcista
  1D : close > EMA50 y close > EMA200  → estructura/régimen alcista
  4H : EMA8 > EMA21 y RSI 45-65        → momentum válido
  1H : 3/3 condiciones                 → entrada
       a) cierre cruza EMA21 al alza  b) RSI cruza ~50 al alza  c) RSI 40-65

Stop = max( mínimo de los últimos 10 lows 1H, entry - ATR_MULT * ATR_4H ).
Gestión de salida (configurable por params, leída por el backtester vía exit_cfg):
  - tp1_rr / tp2_rr: take-profits en múltiplos de R
  - tp1_frac:        fracción que se cierra en TP1 (1.0 = salida única en TP1)
  - breakeven_after_tp1: mover stop a entrada tras TP1
  - trail_mult:      trailing stop tipo chandelier por ATR (0 = off)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .. import indicators as ind
from .base import Strategy, align_higher, align_value


class MTFEmaRsi(Strategy):
    name = "mtf_ema_rsi"
    base_tf = "1h"
    aux_tfs = ("4h", "1d", "1w")

    def __init__(self, params: dict):
        super().__init__(params)
        self.exit_cfg = {
            "tp1_frac": params.get("tp1_frac", 1.0),
            "breakeven_after_tp1": params.get("breakeven_after_tp1", False),
            "trail_mult": params.get("trail_mult", 0.0),
        }

    def prepare(self, frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
        p = self.p
        out = frames["1h"].copy()
        f4, f1d, f1w = frames["4h"], frames["1d"], frames["1w"]

        ema20_1w = ind.ema(f1w["close"], 20)
        bias_bull = align_higher(f1w["close"] > ema20_1w * (1 + p["ema_buffer"]), out.index)

        ema50_1d = ind.ema(f1d["close"], 50)
        ema200_1d = ind.ema(f1d["close"], 200)
        daily_ok = align_higher(
            (f1d["close"] > ema50_1d) & (f1d["close"] > ema200_1d), out.index)

        ema8_4h = ind.ema(f4["close"], 8)
        ema21_4h = ind.ema(f4["close"], 21)
        rsi_4h = ind.rsi(f4["close"], p["rsi_periodo"])
        atr_4h = ind.atr(f4, p["atr_periodo"])
        setup_4h = align_higher(
            (ema8_4h > ema21_4h) & rsi_4h.between(45, 65), out.index)
        atr_ref = align_value(atr_4h, out.index).fillna(ind.atr(out, p["atr_periodo"]))

        ema21_1h = ind.ema(out["close"], 21)
        rsi_1h = ind.rsi(out["close"], p["rsi_periodo"])
        out["rsi"] = rsi_1h
        cond_a = (out["close"].shift(1) < ema21_1h.shift(1)) & (out["close"] > ema21_1h)
        cond_b = (rsi_1h.shift(1) < 52) & (rsi_1h > 48)
        cond_c = rsi_1h.between(40, 65)
        entry_1h = cond_a & cond_b & cond_c

        low_min10 = out["low"].rolling(10).min()
        stop = np.maximum(low_min10, out["close"] - p["atr_mult_stop"] * atr_ref)
        risk = out["close"] - stop

        out["long_entry"] = bias_bull & daily_ok & setup_4h & entry_1h & (risk > 0)
        out["long_exit"] = False
        out["stop"] = stop
        out["atr"] = atr_ref
        if p.get("use_targets", True):
            out["tp1"] = out["close"] + risk * p.get("tp1_rr", 2.0)
            out["tp2"] = out["close"] + risk * p.get("tp2_rr", 3.0)
        return out

    def _entry_reason(self, row) -> str:
        return f"MTF alineado 1W/1D/4H + pullback 1H a EMA21 (RSI {row['rsi']:.0f})"
