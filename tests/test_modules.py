import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
import pandas as pd
import numpy as np
from combination.data import normalize_ohlc
from combination.market_intelligence import analyze_market
from combination.quant_lab import summarize_returns, bootstrap_terminal_returns, simple_walk_forward
from combination.macro_geopolitical import validate_events
from combination.master_engine import combine


def sample(n=160):
    rng = np.random.default_rng(5)
    close = 2000 * np.exp(np.cumsum(rng.normal(.0002, .004, n)))
    return pd.DataFrame({"timestamp": pd.date_range("2025-01-01", periods=n, freq="h", tz="UTC"), "open": close*(1+rng.normal(0,.0005,n)), "high": close*1.003, "low": close*.997, "close": close, "volume": rng.integers(100,1000,n)})


def test_normalize_and_market():
    df = normalize_ohlc(sample())
    assert len(df) == 160
    featured, market = analyze_market(df)
    assert "rsi14" in featured.columns
    assert market["trend"]


def test_quant():
    df = sample()
    summary = summarize_returns(df)
    boot = bootstrap_terminal_returns(df, horizon=5, simulations=300)
    wf = simple_walk_forward(df)
    assert summary["n_returns"] == 159
    assert boot["simulations"] == 300
    assert 0 <= wf["test_directional_hit_rate"] <= 1


def test_events_and_master():
    ev = validate_events(pd.DataFrame([{"date_utc":"2025-01-01", "title":"test", "bias_gold":"bullish", "confidence":.8}]))
    assert len(ev) == 1
    _, market = analyze_market(sample())
    master = combine(market, events=ev.to_dict("records"))
    assert "heuristic_score" in master
    assert len(master["scenarios"]) == 3


def test_bad_ohlc_rejected():
    df = sample(40)
    df.loc[0, "high"] = 1
    try:
        normalize_ohlc(df)
    except ValueError:
        return
    raise AssertionError("OHLC inválido debería rechazarse")
