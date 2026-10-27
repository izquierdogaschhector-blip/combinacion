"""Configurable market-data providers with defensive validation."""
from __future__ import annotations
import requests
import pandas as pd
from .data import normalize_ohlc

TWELVE_SYMBOLS = {
    "XAUUSD": "XAU/USD",
    "EURUSD": "EUR/USD",
    "EURJPY": "EUR/JPY",
    "DXY": "DXY",
    "US10Y": "US10Y",
}
TWELVE_INTERVALS = {"15m": "15min", "30m": "30min", "1h": "1h", "2h": "2h", "4h": "4h", "1d": "1day", "1day": "1day"}


def download_twelvedata(asset: str, api_key: str, interval: str = "1h", outputsize: int = 500) -> tuple[pd.DataFrame, dict]:
    """Fetch OHLC from Twelve Data. User must have access to requested symbol/interval."""
    if not api_key or not api_key.strip():
        raise ValueError("Introduce tu API key de Twelve Data en la barra lateral.")
    if asset not in TWELVE_SYMBOLS:
        raise ValueError(f"Activo no configurado para Twelve Data: {asset}")
    if interval not in TWELVE_INTERVALS:
        raise ValueError(f"Intervalo no compatible: {interval}")
    params = {
        "symbol": TWELVE_SYMBOLS[asset],
        "interval": TWELVE_INTERVALS[interval],
        "outputsize": max(1, min(int(outputsize), 5000)),
        "timezone": "UTC",
        "apikey": api_key.strip(),
    }
    try:
        response = requests.get("https://api.twelvedata.com/time_series", params=params, timeout=(5, 25))
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Error de conexión con Twelve Data: {exc}") from exc
    if payload.get("status") == "error" or "values" not in payload:
        message = payload.get("message") or payload.get("code") or str(payload)[:500]
        raise RuntimeError(f"Twelve Data no devolvió series: {message}. Revisa símbolo, plan y créditos.")
    values = payload.get("values") or []
    if not values:
        raise RuntimeError("Twelve Data devolvió cero velas para este símbolo e intervalo.")
    frame = pd.DataFrame(values).rename(columns={"datetime": "timestamp"})
    frame = normalize_ohlc(frame)
    meta = {
        "provider": "Twelve Data",
        "provider_symbol": TWELVE_SYMBOLS[asset],
        "requested_asset": asset,
        "interval": interval,
        "rows": int(len(frame)),
        "latest_timestamp_utc": str(frame.timestamp.iloc[-1]),
        "provider_timezone": payload.get("meta", {}).get("exchange_timezone", "UTC/requested"),
        "proxy_note": "XAU/USD es el símbolo spot de oro de Twelve Data si tu plan lo incluye; no es un libro centralizado. Comprueba cobertura y retraso en tu cuenta.",
    }
    return frame, meta
