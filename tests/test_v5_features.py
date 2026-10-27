import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import pandas as pd
import pytest
from combination.orderflow import analyze_trades
from combination.cot import analyze_cot_csv
from combination.agent_sim import simulate_agents
from combination.validation import evaluate_momentum_baseline
from combination.storage import Store


def test_orderflow_requires_side_or_bidask():
    d = pd.DataFrame({'timestamp':['2026-01-01T00:00:00Z'], 'price':[100], 'volume':[2]})
    with pytest.raises(ValueError, match='No hay side ni bid/ask'):
        analyze_trades(d)


def test_orderflow_signed_volume():
    d = pd.DataFrame({'timestamp':['2026-01-01T00:00:00Z','2026-01-01T00:00:10Z'], 'price':[100,101], 'volume':[2,3], 'side':['buy','sell']})
    bars, summary = analyze_trades(d)
    assert summary['total_volume'] == 5
    assert summary['signed_delta'] == -1
    assert summary['classified_volume_fraction'] == 1
    assert len(bars) == 1


def test_cot_filter_and_net_positions():
    d = pd.DataFrame({'Market_and_Exchange_Names':['GOLD - COMEX','SILVER - COMEX'], 'Report_Date_as_YYYY-MM-DD':['2026-01-01','2026-01-01'], 'NonComm_Positions_Long_All':[100,50], 'NonComm_Positions_Short_All':[40,20]})
    filtered, summary = analyze_cot_csv(d, 'GOLD')
    assert len(filtered) == 1
    assert summary['latest_net_position'] == 60


def test_agent_sim_deterministic():
    a = simulate_agents(steps=20, simulations=100, seed=123)
    b = simulate_agents(steps=20, simulations=100, seed=123)
    assert a['terminal_return_q50'] == b['terminal_return_q50']
    assert 'No está calibrada' in a['warning']


def test_validation_temporal_split():
    n=200
    close = [100]
    for i in range(1,n): close.append(close[-1]*(1.001 if i%3 else .999))
    d = pd.DataFrame({'timestamp':pd.date_range('2025-01-01', periods=n, freq='h', tz='UTC'), 'open':close, 'high':[x*1.002 for x in close], 'low':[x*.998 for x in close], 'close':close})
    result = evaluate_momentum_baseline(d, horizon=2)
    assert result['test_observations'] > 20
    assert 'cronológico' in result['method']


def test_store_persists_event_and_analysis(tmp_path):
    store = Store(tmp_path/'test.sqlite3')
    store.save_event({'date_utc':'2026-01-01T00:00:00+00:00','title':'test','bias_gold':'unknown','confidence':0.5})
    assert len(store.load_events()) == 1
    aid = store.save_analysis('XAUUSD','1h','test',{}, {'last_close':1},{},{})
    assert aid == 1
    assert len(store.recent_analyses()) == 1


def test_cot_api_uses_public_endpoint(monkeypatch):
    from combination.cot import fetch_cot_api
    class Response:
        def raise_for_status(self): pass
        def json(self): return [{'market_and_exchange_names':'GOLD - COMEX','report_date_as_yyyy_mm_dd':'2026-01-01'}]
    calls = {}
    def fake_get(url, **kwargs):
        calls['url'] = url; calls['kwargs'] = kwargs
        return Response()
    # requests is imported inside the function, so patch the module package.
    import requests
    monkeypatch.setattr(requests, 'get', fake_get)
    df = fetch_cot_api('72hh-3qpy', 'GOLD', 100)
    assert len(df) == 1
    assert 'publicreporting.cftc.gov/resource/72hh-3qpy.json' in calls['url']
