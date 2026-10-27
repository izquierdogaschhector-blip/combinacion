"""Fetch user-selected RSS feeds; feed contents are untrusted data."""
from __future__ import annotations
import pandas as pd
import requests
import xml.etree.ElementTree as ET


def fetch_rss(urls: list[str], limit_per_feed: int = 15) -> pd.DataFrame:
    rows = []
    for url in urls:
        url = (url or "").strip()
        if not url:
            continue
        if not url.lower().startswith(("https://", "http://")):
            raise ValueError(f"URL RSS no válida: {url}")
        try:
            resp = requests.get(url, timeout=(5, 15), headers={"User-Agent": "CombinacionMaestra/4.0"})
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception as exc:
            rows.append({"source_url": url, "title": "ERROR DE LECTURA", "published": "", "summary": str(exc)[:300]})
            continue
        for item in root.findall(".//item")[:limit_per_feed]:
            title = item.findtext("title", default="").strip()
            link = item.findtext("link", default="").strip()
            published = item.findtext("pubDate", default="").strip()
            summary = item.findtext("description", default="").strip()
            rows.append({"source_url": url, "title": title, "link": link, "published": published, "summary": summary[:1500]})
        # Atom feeds use namespaces; handle common entries defensively.
        if not root.findall(".//item"):
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall(".//atom:entry", ns)[:limit_per_feed]:
                title = entry.findtext("atom:title", default="", namespaces=ns).strip()
                link_el = entry.find("atom:link", ns)
                link = link_el.attrib.get("href", "") if link_el is not None else ""
                published = entry.findtext("atom:updated", default="", namespaces=ns).strip()
                summary = entry.findtext("atom:summary", default="", namespaces=ns).strip()
                rows.append({"source_url": url, "title": title, "link": link, "published": published, "summary": summary[:1500]})
    return pd.DataFrame(rows, columns=["source_url", "title", "link", "published", "summary"])


def classify_headlines(frame: pd.DataFrame) -> pd.DataFrame:
    """Transparent keyword triage. Labels are hypotheses for human review, not verified sentiment."""
    if frame is None or frame.empty:
        return pd.DataFrame(columns=list(frame.columns) + ['topic','gold_bias_hypothesis','triage_confidence','review_note'])
    rows = []
    groups = {
        'monetary_policy': ['federal reserve','fed ','interest rate','rate cut','rate hike','central bank','monetary policy','fomc','ecb','boj'],
        'inflation': ['inflation','cpi','pce','consumer price','producer price'],
        'employment_growth': ['payroll','unemployment','employment','jobs report','gdp','growth'],
        'geopolitics': ['war','attack','conflict','sanction','missile','ceasefire','invasion','geopolitical'],
        'financial_risk': ['bank failure','liquidity crisis','default','credit risk','market stress'],
        'gold_supply_demand': ['gold demand','gold reserves','central bank gold','gold mine','bullion']}
    for _, r in frame.iterrows():
        title = str(r.get('title',''))
        text = (title + ' ' + str(r.get('summary',''))).lower()
        topics = [topic for topic, words in groups.items() if any(w in text for w in words)]
        # Direction intentionally stays mixed/unknown: headlines alone rarely establish gold's net reaction.
        rows.append({**r.to_dict(), 'topic': ', '.join(topics) if topics else 'unclassified',
                     'gold_bias_hypothesis':'mixed/needs review', 'triage_confidence': min(.75, .35 + .1*len(topics)) if topics else .2,
                     'review_note':'Clasificación por palabras clave. Verifica la noticia original, sorpresa frente a expectativas y reacción observada antes de asignar sesgo.'})
    return pd.DataFrame(rows)
