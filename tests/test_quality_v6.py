import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
import pandas as pd
from datetime import datetime, timezone
from combination.quality import assess_ohlc_quality
from combination.master_engine import combine

def frame(n=120):
    ts = pd.date_range('2026-10-20', periods=n, freq='h', tz='UTC')
    close = [100 + i * 0.1 for i in range(n)]
    return pd.DataFrame({'timestamp':ts,'open':close,'high':[x+0.2 for x in close], 'low':[x-0.2 for x in close], 'close':close})

def test_quality_report_basic():
    result = assess_ohlc_quality(frame(), '1h', now=datetime(2026,10,25,tzinfo=timezone.utc))
    assert result['rows'] == 120
    assert result['score'] >= 0 and result['score'] <= 100
    assert result['latest_timestamp_utc'] is not None

def test_quality_empty_frame():
    result = assess_ohlc_quality(pd.DataFrame(), '1h')
    assert result['status'] == 'error'
    assert result['score'] == 0

def test_news_is_context_not_directional_score():
    market = {'trend':'neutral','momentum_20_bars':0,'recent_high_20':101,'recent_low_20':99}
    a = combine(market)
    b = combine(market, news_items=[{'topic':'geopolitics','title':'Headline'}])
    assert a['heuristic_score'] == b['heuristic_score']
    assert b['news_items_considered'] == 1
    assert b['news_topics']['geopolitics'] == 1
    assert any('Titulares integrados solo como contexto' in x for x in b['limitations'])
