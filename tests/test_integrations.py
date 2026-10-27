import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pandas as pd
import pytest
from combination.providers import download_twelvedata
from combination.ai_analysis import analyze_with_ai
from combination.news import fetch_rss

class FakeResponse:
    def __init__(self, payload, status_code=200, content=None):
        self._payload = payload
        self.status_code = status_code
        self.content = content if content is not None else b""
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")
    def json(self):
        return self._payload


def test_twelvedata_normalizes_ohlc(monkeypatch):
    def fake_get(*args, **kwargs):
        return FakeResponse({"meta": {"exchange_timezone": "UTC"}, "values": [
            {"datetime":"2026-01-02 10:00:00", "open":"10", "high":"12", "low":"9", "close":"11"},
            {"datetime":"2026-01-02 11:00:00", "open":"11", "high":"13", "low":"10", "close":"12"},
        ]})
    monkeypatch.setattr("combination.providers.requests.get", fake_get)
    df, meta = download_twelvedata("EURUSD", "fake", "1h", 100)
    assert len(df) == 2
    assert list(df.columns[:5]) == ["timestamp", "open", "high", "low", "close"]
    assert meta["provider"] == "Twelve Data"


def test_twelvedata_requires_key():
    with pytest.raises(ValueError):
        download_twelvedata("EURUSD", "", "1h", 100)


def test_rss_parses_basic_xml(monkeypatch):
    xml = b"<rss><channel><item><title>Test headline</title><link>https://example.com/a</link><pubDate>Mon</pubDate><description>Summary</description></item></channel></rss>"
    monkeypatch.setattr("combination.news.requests.get", lambda *a, **k: FakeResponse({}, content=xml))
    df = fetch_rss(["https://example.com/rss"])
    assert len(df) == 1
    assert df.iloc[0]["title"] == "Test headline"


def test_ai_requires_key():
    with pytest.raises(ValueError):
        analyze_with_ai("gemini", "", "gemini-2.5-flash", {})
