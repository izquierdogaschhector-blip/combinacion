"""Data-quality and freshness checks for market OHLC frames."""
from __future__ import annotations
from datetime import datetime, timezone
import pandas as pd

INTERVAL_MINUTES = {"1m":1, "5m":5, "15m":15, "30m":30, "45m":45, "1h":60, "2h":120, "4h":240, "1d":1440, "1day":1440}

def assess_ohlc_quality(frame: pd.DataFrame, interval: str = "1h", now: datetime | None = None) -> dict:
    """Return a transparent diagnostic; it does not alter the source data."""
    if frame is None or frame.empty:
        return {"status":"error", "score":0, "rows":0, "issues":["No hay datos OHLC"], "latest_timestamp_utc":None, "age_minutes":None, "duplicate_timestamps":0, "non_monotonic_timestamps":0, "missing_bar_gaps":0}
    d = frame.copy()
    if "timestamp" not in d:
        return {"status":"error", "score":0, "rows":len(d), "issues":["Falta columna timestamp"], "latest_timestamp_utc":None, "age_minutes":None, "duplicate_timestamps":0, "non_monotonic_timestamps":0, "missing_bar_gaps":0}
    ts = pd.to_datetime(d["timestamp"], errors="coerce", utc=True)
    bad_ts = int(ts.isna().sum())
    valid = ts.dropna()
    duplicates = int(valid.duplicated().sum())
    non_monotonic = int((valid.diff().dropna() < pd.Timedelta(0)).sum())
    minutes = INTERVAL_MINUTES.get(interval, 60)
    gaps = int((valid.sort_values().diff().dropna() > pd.Timedelta(minutes=minutes * 2.5)).sum())
    latest = valid.max() if len(valid) else pd.NaT
    now = now or datetime.now(timezone.utc)
    now_ts = pd.Timestamp(now)
    if now_ts.tzinfo is None:
        now_ts = now_ts.tz_localize("UTC")
    age = max(0.0, (now_ts - latest).total_seconds()/60) if pd.notna(latest) else None
    # For markets with closures/weekends, freshness is a warning rather than proof of failure.
    issues = []
    if len(d) < 100: issues.append("Menos de 100 velas: análisis estadístico provisional")
    if bad_ts: issues.append(f"{bad_ts} timestamps no interpretables")
    if duplicates: issues.append(f"{duplicates} timestamps duplicados")
    if non_monotonic: issues.append(f"{non_monotonic} timestamps fuera de orden")
    if gaps: issues.append(f"{gaps} huecos amplios entre velas; pueden ser cierres de mercado o datos faltantes")
    freshness_limit = max(minutes * 3, 24*60 if interval in ("1d", "1day") else minutes*3)
    if age is not None and age > freshness_limit:
        issues.append(f"Última vela tiene {age:.0f} minutos; confirma horario del mercado y retraso del proveedor")
    score = max(0, 100 - min(35, bad_ts*5) - min(25, duplicates*5) - min(15, non_monotonic*3) - min(15, gaps) - (10 if len(d)<100 else 0) - (10 if age is not None and age>freshness_limit else 0))
    status = "ok" if score >= 85 and not bad_ts and not duplicates else "warning" if score >= 60 else "error"
    return {"status":status,"score":score,"rows":int(len(d)),"issues":issues,"latest_timestamp_utc":str(latest) if pd.notna(latest) else None,"age_minutes":round(age,1) if age is not None else None,"duplicate_timestamps":duplicates,"non_monotonic_timestamps":non_monotonic,"invalid_timestamps":bad_ts,"missing_bar_gaps":gaps,"interval":interval,"note":"Los huecos pueden ser normales por fines de semana, festivos o sesiones; revisa antes de interpretarlos como errores."}
