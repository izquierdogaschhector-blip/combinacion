"""Manual event ledger and optional FRED series retrieval."""
from __future__ import annotations
import pandas as pd

EVENT_COLUMNS = ["date_utc", "title", "category", "source", "source_url", "impact_channel", "bias_gold", "confidence", "notes"]


def validate_events(events: pd.DataFrame) -> pd.DataFrame:
    if events is None or events.empty:
        return pd.DataFrame(columns=EVENT_COLUMNS)
    d = events.copy()
    d.columns = [str(c).strip().lower() for c in d.columns]
    for col in EVENT_COLUMNS:
        if col not in d.columns:
            d[col] = ""
    d["date_utc"] = pd.to_datetime(d["date_utc"], errors="coerce", utc=True)
    d = d.dropna(subset=["date_utc"])
    d["confidence"] = pd.to_numeric(d["confidence"], errors="coerce").clip(0, 1)
    allowed = {"bullish", "bearish", "mixed", "unknown"}
    d["bias_gold"] = d["bias_gold"].astype(str).str.lower().where(d["bias_gold"].astype(str).str.lower().isin(allowed), "unknown")
    return d[EVENT_COLUMNS].sort_values("date_utc", ascending=False).reset_index(drop=True)


def fetch_fred_series(series_id: str, api_key: str, start: str = "2015-01-01") -> pd.DataFrame:
    """Fetch FRED series via official API; requires user's own API key."""
    if not api_key:
        raise ValueError("Introduce tu propia clave API de FRED en la configuración.")
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("Instala requests: pip install requests") from exc
    url = "https://api.stlouisfed.org/fred/series/observations"
    response = requests.get(url, params={"series_id": series_id, "api_key": api_key, "file_type": "json", "observation_start": start}, timeout=25)
    response.raise_for_status()
    payload = response.json()
    if "observations" not in payload:
        raise RuntimeError(f"Respuesta FRED inesperada: {payload}")
    df = pd.DataFrame(payload["observations"])
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df[["date", "value"]].dropna().reset_index(drop=True)
