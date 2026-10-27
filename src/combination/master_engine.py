"""Rule-based integration. The score is explicitly heuristic, not a calibrated probability."""
from __future__ import annotations
from datetime import datetime, timezone


def combine(market: dict, quant: dict | None = None, events: list[dict] | None = None,
            macro_context: dict | None = None, orderflow: dict | None = None,
            positioning: dict | None = None, data_quality: dict | None = None, news_items: list[dict] | None = None) -> dict:
    quant, events, macro_context = quant or {}, events or [], macro_context or {}
    orderflow, positioning, data_quality = orderflow or {}, positioning or {}, data_quality or {}
    news_items = news_items or []
    # Headlines are included as context only. Keyword tags do not create directional score.
    news_topics = {}
    for item in news_items:
        for topic in str(item.get("topic", "unclassified")).split(", "):
            news_topics[topic] = news_topics.get(topic, 0) + 1
    trend = market.get('trend', 'mixta/neutral')
    momentum = float(market.get('momentum_20_bars', 0) or 0)
    price_score = 1 if trend == 'alcista' else -1 if trend == 'bajista' else 0
    momentum_score = 1 if momentum > .002 else -1 if momentum < -.002 else 0
    # Only explicitly classified, confidence-weighted events are considered; unknown/mixed add no direction.
    event_score_raw = 0.0
    for event in events:
        bias = str(event.get('bias_gold','unknown')).lower()
        try: conf = max(0.0, min(1.0, float(event.get('confidence', 0) or 0)))
        except (TypeError, ValueError): conf = 0.0
        if bias == 'bullish': event_score_raw += conf
        elif bias == 'bearish': event_score_raw -= conf
    event_score = max(-2.0, min(2.0, event_score_raw))
    # Orderflow contribution is intentionally not used in directional score unless user-supplied signed data is present.
    delta_ratio = orderflow.get('delta_ratio')
    flow_note = 'Sin Order Flow válido conectado.'
    flow_score = 0
    if delta_ratio is not None:
        try:
            delta_ratio = float(delta_ratio)
            if delta_ratio > .1: flow_score = 1
            elif delta_ratio < -.1: flow_score = -1
            flow_note = 'Order Flow calculado exclusivamente sobre el archivo/feed aportado; no consolidado.'
        except (TypeError, ValueError):
            delta_ratio = None
    score = price_score + momentum_score + event_score + flow_score
    if score >= 2: bias = 'sesgo alcista heurístico'
    elif score <= -2: bias = 'sesgo bajista heurístico'
    else: bias = 'lectura mixta / neutral'
    contradictions = []
    if price_score > 0 and event_score < -.25: contradictions.append('precio alcista frente a eventos registrados bajistas')
    if price_score < 0 and event_score > .25: contradictions.append('precio bajista frente a eventos registrados alcistas')
    if price_score > 0 and flow_score < 0: contradictions.append('estructura alcista frente al delta negativo del feed aportado')
    if price_score < 0 and flow_score > 0: contradictions.append('estructura bajista frente al delta positivo del feed aportado')
    scenarios = [
        {'name':'Continuación', 'condition':f'La estructura y el momentum persisten; validar cierre por encima de {market.get("recent_high_20", "nivel no disponible")} para continuidad alcista o por debajo de {market.get("recent_low_20", "nivel no disponible")} para bajista.', 'invalidates':'Recuperación/pérdida de la estructura reciente en dirección opuesta.'},
        {'name':'Reversión', 'condition':'Se rompe la estructura reciente y el momentum cambia; buscar confirmación, no anticipar por un titular aislado.', 'invalidates':'El precio recupera la estructura previa y el momentum vuelve a su régimen anterior.'},
        {'name':'Rango', 'condition':'No hay ruptura confirmada y el precio permanece entre los extremos recientes.', 'invalidates':'Cierre sostenido fuera del rango con confirmación posterior.'},
    ]
    limitations = [
        'La puntuación es una regla heurística, no una probabilidad ni una recomendación de operación.',
        'Los eventos registrados pueden estar incompletos; los titulares requieren revisión humana.',
        'Las relaciones entre oro, dólar y rendimientos cambian por régimen y horizonte.',
        'El Order Flow solo representa el feed aportado; no representa todo el mercado OTC de XAUUSD.',
        'El posicionamiento COT es semanal y de futuros/opciones, no flujo intradía spot.',
        'Los resultados cuantitativos históricos no garantizan comportamiento futuro; comprobar costes y estabilidad.',
        'No se generan ni ejecutan órdenes y no es asesoramiento financiero personalizado.'
    ]
    if news_items:
        limitations.append('Titulares integrados solo como contexto temático; no alteran el sesgo direccional automáticamente.')
    if data_quality.get('rows', 0) and data_quality.get('rows', 0) < 100:
        limitations.append('Historial pequeño: tratar los indicadores y estadísticas como provisionales.')
    return {'overall_reading':bias, 'heuristic_score':round(float(score),3),
            'score_components':{'price_trend':price_score,'momentum':momentum_score,'registered_events_confidence_weighted':round(event_score,3),'provided_feed_delta':flow_score},
            'contradictions':contradictions,'scenarios':scenarios,'events_used':len(events), 'news_items_considered':len(news_items), 'news_topics':news_topics,
            'orderflow_note':flow_note,'quant_context':quant,'macro_context':macro_context,
            'positioning_context':positioning,'data_quality':data_quality,
            'probabilities':'No calculadas: la puntuación heurística no equivale a una probabilidad calibrada.',
            'limitations':limitations}
