"""Order-flow proxies from user-supplied trade/tick data; never invents missing bid/ask volume."""
from __future__ import annotations
import pandas as pd


def analyze_trades(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    if frame is None or frame.empty:
        raise ValueError('El CSV de ticks está vacío.')
    d = frame.copy()
    d.columns = [str(c).strip().lower().replace(' ', '_') for c in d.columns]
    aliases = {'datetime':'timestamp','date':'timestamp','time':'timestamp','qty':'volume','size':'volume','last':'price','trade_price':'price'}
    d = d.rename(columns={k:v for k,v in aliases.items() if k in d.columns and v not in d.columns})
    if not {'timestamp','price','volume'}.issubset(d.columns):
        raise ValueError('El CSV de ticks necesita timestamp, price y volume; opcionalmente side, bid y ask.')
    d['timestamp'] = pd.to_datetime(d['timestamp'], errors='coerce', utc=True)
    d['price'] = pd.to_numeric(d['price'], errors='coerce')
    d['volume'] = pd.to_numeric(d['volume'], errors='coerce')
    d = d.dropna(subset=['timestamp','price','volume']).sort_values('timestamp')
    if d.empty or (d.volume < 0).any() or (d.price <= 0).any():
        raise ValueError('No hay operaciones válidas, o hay precios/volúmenes inválidos.')
    method = 'sin clasificar'
    if 'side' in d.columns:
        side = d['side'].astype(str).str.lower().str.strip()
        mapping = {'buy':1,'b':1,'ask':1,'buyer':1,'sell':-1,'s':-1,'bid':-1,'seller':-1}
        d['sign'] = side.map(mapping)
        if d.sign.notna().mean() < .8:
            raise ValueError('La columna side debe usar buy/sell (o b/s, ask/bid) en al menos el 80% de las filas.')
        method = 'side provisto por la fuente'
    elif {'bid','ask'}.issubset(d.columns):
        d['bid'] = pd.to_numeric(d['bid'], errors='coerce')
        d['ask'] = pd.to_numeric(d['ask'], errors='coerce')
        d['sign'] = 0
        d.loc[d.price >= d.ask, 'sign'] = 1
        d.loc[d.price <= d.bid, 'sign'] = -1
        method = 'clasificación por cruce bid/ask; trades dentro del spread quedan neutrales'
    else:
        raise ValueError('No hay side ni bid/ask. No se calculará delta inventado; añade una columna side o bid y ask.')
    d['signed_volume'] = d.volume * d.sign.fillna(0)
    d['minute'] = d.timestamp.dt.floor('min')
    grouped = d.groupby('minute', as_index=False).agg(total_volume=('volume','sum'), signed_delta=('signed_volume','sum'), trades=('price','count'), vwap=('price', lambda x: float((x*d.loc[x.index,'volume']).sum()/d.loc[x.index,'volume'].sum())))
    total = float(d.volume.sum())
    delta = float(d.signed_volume.sum())
    classified_volume = float(d.loc[d.sign != 0, 'volume'].sum())
    summary = {'trades': int(len(d)), 'total_volume': total, 'signed_delta': delta, 'delta_ratio': delta / total if total else 0.0,
               'classified_volume_fraction': classified_volume / total if total else 0.0, 'classification_method': method,
               'start_utc': str(d.timestamp.min()), 'end_utc': str(d.timestamp.max()),
               'warning': 'Representa solo el feed aportado. No equivale a flujo consolidado de todo XAUUSD OTC ni revela identidad/intención de participantes.'}
    return grouped, summary
