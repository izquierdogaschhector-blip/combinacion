"""Market state analysis: descriptive OHLC features, not order-flow observation."""
import numpy as np
import pandas as pd
from .data import normalize_ohlc


def analyze_market(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    d = normalize_ohlc(frame)
    if len(d) < 30:
        raise ValueError("Se requieren al menos 30 velas para un análisis mínimamente estable.")
    c, h, l = d.close, d.high, d.low
    d["return"] = c.pct_change()
    d["ema20"] = c.ewm(span=20, adjust=False).mean()
    d["ema50"] = c.ewm(span=50, adjust=False).mean()
    d["sma20"] = c.rolling(20).mean()
    d["atr14"] = pd.concat([(h-l), (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1).rolling(14).mean()
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    d["rsi14"] = 100 - (100 / (1 + rs))
    last = d.iloc[-1]
    prior = d.iloc[-21]
    momentum20 = float(last.close / prior.close - 1)
    trend = "alcista" if last.ema20 > last.ema50 else "bajista" if last.ema20 < last.ema50 else "neutral"
    if last.close > last.ema20 and trend == "alcista": trend = "alcista"
    elif last.close < last.ema20 and trend == "bajista": trend = "bajista"
    else: trend = "mixta/neutral"
    atr_pct = float(last.atr14 / last.close) if pd.notna(last.atr14) else None
    recent = d.tail(20)
    state = {
        "bars": int(len(d)), "last_close": float(last.close),
        "trend": trend, "momentum_20_bars": momentum20,
        "ema20": float(last.ema20), "ema50": float(last.ema50),
        "rsi14": float(last.rsi14) if pd.notna(last.rsi14) else None,
        "atr14": float(last.atr14) if pd.notna(last.atr14) else None,
        "atr_pct": atr_pct,
        "recent_high_20": float(recent.high.max()),
        "recent_low_20": float(recent.low.min()),
        "last_timestamp_utc": str(last.timestamp),
        "description": "Indicadores derivados de OHLC; no observan directamente liquidez, órdenes, participantes ni intención institucional."
    }
    return d, state
