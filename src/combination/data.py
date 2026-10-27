"""Data access, normalization, validation and provider metadata."""
from __future__ import annotations
import pandas as pd

SYMBOLS = {
    "XAUUSD": "GC=F",  # COMEX gold futures proxy; NOT spot XAUUSD
    "EURUSD": "EURUSD=X",
    "EURJPY": "EURJPY=X",
    "DXY": "DX-Y.NYB",
    "US10Y": "^TNX",
}

REQUIRED = ["timestamp", "open", "high", "low", "close"]


def normalize_ohlc(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize OHLC CSV/dataframe. Accepts timestamp/date/datetime and title case columns."""
    if frame is None or frame.empty:
        raise ValueError("No hay datos. Carga un CSV o descarga datos desde el proveedor.")
    d = frame.copy()
    d.columns = [str(c).strip().lower().replace(" ", "_") for c in d.columns]
    if "timestamp" not in d.columns:
        for candidate in ("datetime", "date", "time"):
            if candidate in d.columns:
                d = d.rename(columns={candidate: "timestamp"})
                break
    # yfinance OHLC columns are commonly title case; normalized above.
    missing = set(REQUIRED) - set(d.columns)
    if missing:
        raise ValueError("Faltan columnas: " + ", ".join(sorted(missing)) + ". Requeridas: timestamp, open, high, low, close.")
    d["timestamp"] = pd.to_datetime(d["timestamp"], errors="coerce", utc=True)
    for col in ["open", "high", "low", "close"]:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    if "volume" in d.columns:
        d["volume"] = pd.to_numeric(d["volume"], errors="coerce")
    d = d.dropna(subset=REQUIRED).sort_values("timestamp").drop_duplicates("timestamp")
    if d.empty:
        raise ValueError("No quedan velas válidas tras limpiar el archivo.")
    if (d[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("Hay precios cero o negativos.")
    if (d["high"] < d[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("OHLC inválido: high por debajo de open/close/low.")
    if (d["low"] > d[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("OHLC inválido: low por encima de open/close/high.")
    return d.reset_index(drop=True)


def download_yahoo(symbol_key: str, period: str = "1y", interval: str = "1h") -> tuple[pd.DataFrame, dict]:
    """Download using yfinance. For XAUUSD uses GC=F futures proxy, not spot."""
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("Falta yfinance. Instala dependencias con el archivo INICIAR_WINDOWS.bat o pip install -r requirements.txt") from exc
    if symbol_key not in SYMBOLS:
        raise ValueError(f"Símbolo no soportado: {symbol_key}")
    symbol = SYMBOLS[symbol_key]
    try:
        raw = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False, threads=False)
    except Exception as exc:
        raise RuntimeError(f"No se pudo descargar {symbol}: {exc}") from exc
    if raw is None or raw.empty:
        raise RuntimeError(f"El proveedor no devolvió datos para {symbol}. Prueba otro intervalo o periodo.")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw = raw.reset_index()
    # yfinance may use Date for daily and Datetime for intraday.
    df = normalize_ohlc(raw)
    metadata = {
        "provider": "Yahoo Finance vía yfinance",
        "provider_symbol": symbol,
        "requested_asset": symbol_key,
        "proxy_note": "GC=F es futuro COMEX de oro; no equivale a spot XAUUSD ni representa su libro de órdenes." if symbol_key == "XAUUSD" else "Cotización referencial del proveedor; puede ser retrasada y no coincidir con broker.",
        "period": period,
        "interval": interval,
        "rows": len(df),
        "latest_timestamp_utc": str(df.timestamp.iloc[-1]),
    }
    return df, metadata
