"""Local SQLite persistence for bars, events, analysis snapshots and evaluations."""
from __future__ import annotations
import json, sqlite3
from pathlib import Path
from typing import Any
import pandas as pd

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "combinacion_maestra.sqlite3"

class Store:
    def __init__(self, path: str | Path = DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self):
        with self._connect() as c:
            c.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS bars (
              asset TEXT NOT NULL, timeframe TEXT NOT NULL, timestamp TEXT NOT NULL,
              open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL, close REAL NOT NULL,
              volume REAL, provider TEXT, saved_at TEXT DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY(asset,timeframe,timestamp,provider));
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, date_utc TEXT, title TEXT NOT NULL,
              category TEXT, source TEXT, source_url TEXT, impact_channel TEXT,
              bias_gold TEXT, confidence REAL, notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS analyses (
              id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
              asset TEXT, timeframe TEXT, provider TEXT, metadata_json TEXT,
              market_json TEXT, quant_json TEXT, master_json TEXT, ai_text TEXT);
            CREATE TABLE IF NOT EXISTS evaluations (
              id INTEGER PRIMARY KEY AUTOINCREMENT, analysis_id INTEGER, evaluated_at TEXT DEFAULT CURRENT_TIMESTAMP,
              asset TEXT, horizon_bars INTEGER, entry_price REAL, future_price REAL,
              realized_return REAL, predicted_bias TEXT, outcome TEXT, notes TEXT,
              FOREIGN KEY(analysis_id) REFERENCES analyses(id));
            CREATE TABLE IF NOT EXISTS source_status (
              id INTEGER PRIMARY KEY AUTOINCREMENT, checked_at TEXT DEFAULT CURRENT_TIMESTAMP,
              source TEXT, status TEXT, detail TEXT);
            CREATE INDEX IF NOT EXISTS idx_bars_asset_time ON bars(asset,timeframe,timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_date ON events(date_utc);
            """)

    def save_bars(self, asset: str, timeframe: str, frame: pd.DataFrame, provider: str):
        rows = []
        for r in frame.itertuples(index=False):
            rows.append((asset, timeframe, pd.Timestamp(r.timestamp).isoformat(), float(r.open), float(r.high), float(r.low), float(r.close),
                         float(r.volume) if hasattr(r, 'volume') and pd.notna(r.volume) else None, provider))
        with self._connect() as c:
            c.executemany("INSERT OR REPLACE INTO bars(asset,timeframe,timestamp,open,high,low,close,volume,provider) VALUES(?,?,?,?,?,?,?,?,?)", rows)

    def save_event(self, event: dict[str, Any]) -> int:
        with self._connect() as c:
            cur = c.execute("INSERT INTO events(date_utc,title,category,source,source_url,impact_channel,bias_gold,confidence,notes) VALUES(?,?,?,?,?,?,?,?,?)",
                (str(event.get('date_utc','')), str(event.get('title','')).strip(), str(event.get('category','')), str(event.get('source','')), str(event.get('source_url','')), str(event.get('impact_channel','')), str(event.get('bias_gold','unknown')), float(event.get('confidence',0.0) or 0.0), str(event.get('notes',''))))
            return int(cur.lastrowid)

    def load_events(self, limit: int = 1000) -> pd.DataFrame:
        with self._connect() as c:
            df = pd.read_sql_query("SELECT date_utc,title,category,source,source_url,impact_channel,bias_gold,confidence,notes FROM events ORDER BY date_utc DESC LIMIT ?", c, params=(limit,))
        if not df.empty:
            df['date_utc'] = pd.to_datetime(df['date_utc'], errors='coerce', utc=True)
        return df

    def save_analysis(self, asset: str, timeframe: str, provider: str, metadata: dict, market: dict, quant: dict, master: dict, ai_text: str = '') -> int:
        with self._connect() as c:
            cur = c.execute("INSERT INTO analyses(asset,timeframe,provider,metadata_json,market_json,quant_json,master_json,ai_text) VALUES(?,?,?,?,?,?,?,?)",
                (asset, timeframe, provider, json.dumps(metadata, ensure_ascii=False, default=str), json.dumps(market, ensure_ascii=False, default=str), json.dumps(quant, ensure_ascii=False, default=str), json.dumps(master, ensure_ascii=False, default=str), ai_text or ''))
            return int(cur.lastrowid)

    def recent_analyses(self, limit: int = 100) -> pd.DataFrame:
        with self._connect() as c:
            return pd.read_sql_query("SELECT id,created_at,asset,timeframe,provider,metadata_json,market_json,quant_json,master_json,ai_text FROM analyses ORDER BY id DESC LIMIT ?", c, params=(limit,))

    def save_evaluation(self, **kw):
        with self._connect() as c:
            cur = c.execute("INSERT INTO evaluations(analysis_id,asset,horizon_bars,entry_price,future_price,realized_return,predicted_bias,outcome,notes) VALUES(?,?,?,?,?,?,?,?,?)",
                (kw.get('analysis_id'),kw['asset'],kw['horizon_bars'],kw['entry_price'],kw['future_price'],kw['realized_return'],kw.get('predicted_bias',''),kw.get('outcome',''),kw.get('notes','')))
            return int(cur.lastrowid)

    def evaluations(self, limit: int = 500) -> pd.DataFrame:
        with self._connect() as c:
            return pd.read_sql_query("SELECT * FROM evaluations ORDER BY id DESC LIMIT ?", c, params=(limit,))

    def source_check(self, source: str, status: str, detail: str):
        with self._connect() as c:
            c.execute("INSERT INTO source_status(source,status,detail) VALUES(?,?,?)", (source,status,detail[:1000]))

    def source_history(self, limit: int = 100) -> pd.DataFrame:
        with self._connect() as c:
            return pd.read_sql_query("SELECT * FROM source_status ORDER BY id DESC LIMIT ?", c, params=(limit,))
