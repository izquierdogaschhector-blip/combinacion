from __future__ import annotations
import sys, os, json
from pathlib import Path
from datetime import date
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')
except ImportError:
    pass
sys.path.insert(0, str(Path(__file__).parent / 'src'))
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

def leer_secreto(nombre, valor_predeterminado=""):
    """Lee un secreto de Streamlit Cloud o, como alternativa, del entorno local."""
    try:
        valor = st.secrets.get(nombre, valor_predeterminado)
        if valor:
            return str(valor)
    except Exception:
        pass

    return os.getenv(nombre, valor_predeterminado)
    


def enviar_mensaje_telegram(mensaje):
    import requests

    token = leer_secreto("TELEGRAM_BOT_TOKEN")
    chat_id = leer_secreto("TELEGRAM_CHAT_ID")
    st.sidebar.write("Tipo de chat:", "grupo/canal" if str(chat_id).startswith("-") else "chat privado")
    st.sidebar.write("Longitud del identificador:", len(str(chat_id)) if chat_id else 0)

    if not token or not chat_id:
        return False, "Faltan las credenciales de Telegram en Secrets."

    chat_id = str(chat_id).strip()
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        respuesta = requests.post(
            url,
            data={"chat_id": chat_id, "text": mensaje},
            timeout=15
        )

        try:
            datos = respuesta.json()
        except ValueError:
            return False, (
                f"Telegram devolvió una respuesta no válida "
                f"(HTTP {respuesta.status_code})."
            )

        if respuesta.ok and datos.get("ok"):
            return True, "Mensaje enviado correctamente a Telegram."

        codigo = datos.get("error_code", respuesta.status_code)
        descripcion = datos.get(
            "description", "Motivo desconocido"
        )
        return False, f"Error de Telegram {codigo}: {descripcion}"

    except requests.RequestException:
        return False, (
            "No se pudo conectar con Telegram. "
            "Comprueba la conexión."
        )
        
def diagnosticar_telegram():
    import requests

    token = leer_secreto("TELEGRAM_BOT_TOKEN")
    chat_id = leer_secreto("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        return "Faltan credenciales en Secrets."

    base = f"https://api.telegram.org/bot{token}"

    try:
        bot_resp = requests.get(
            f"{base}/getMe", timeout=15
        )
        bot_data = bot_resp.json()

        if not bot_resp.ok or not bot_data.get("ok"):
            return "No se pudo verificar el bot. Revisa el token."

        bot = bot_data["result"]

        chat_resp = requests.get(
            f"{base}/getChat",
            params={"chat_id": str(chat_id).strip()},
            timeout=15
        )
        chat_data = chat_resp.json()

        if not chat_resp.ok or not chat_data.get("ok"):
            return (
                "Bot verificado: @" + bot.get("username", "sin_usuario")
                + ". No se pudo consultar el chat: "
                + str(chat_data.get("description", "error desconocido"))
            )

        chat = chat_data["result"]
        mismo_id = str(bot["id"]) == str(chat.get("id"))

        return (
            "Bot que usa la aplicación: @"
            + bot.get("username", "sin_usuario")
            + " | Destino consultado: "
            + chat.get("type", "tipo desconocido")
            + " | Usuario destino: @"
            + chat.get("username", "sin_usuario")
            + " | El destino es el propio bot: "
            + ("Sí" if mismo_id else "No")
        )

    except Exception:
        return "No se pudo completar el diagnóstico de Telegram."




from combination.data import download_yahoo, normalize_ohlc
from combination.providers import download_twelvedata
from combination.ai_analysis import analyze_with_ai
from combination.news import fetch_rss, classify_headlines
from combination.market_intelligence import analyze_market
from combination.quant_lab import summarize_returns, bootstrap_terminal_returns, simple_walk_forward
from combination.macro_geopolitical import validate_events, fetch_fred_series
from combination.master_engine import combine
from combination.storage import Store
from combination.orderflow import analyze_trades
from combination.cot import analyze_cot_csv, fetch_cot_api, CFTC_DATASETS
from combination.agent_sim import simulate_agents
from combination.validation import evaluate_momentum_baseline
from combination.quality import assess_ohlc_quality

APP_DIR = Path(__file__).parent
store = Store(APP_DIR / 'data' / 'combinacion_maestra.sqlite3')
st.set_page_config(page_title='Combinación Maestra V6', layout='wide', initial_sidebar_state='expanded')
st.title('COMBINACIÓN MAESTRA — V6.0')
st.caption('Inteligencia de mercado · Order Flow desde datos aportados · Macro/geopolítica · Posicionamiento COT · Laboratorio cuantitativo · Historial persistente')
st.warning('Aplicación de investigación, no ejecuta operaciones. La puntuación maestra es heurística, no una probabilidad calibrada. No se simulan datos reales. Comprueba siempre proveedor, símbolo, retraso y permisos de tu plan.')

if 'df' not in st.session_state:
    st.session_state.df = None
    st.session_state.metadata = {}
    st.session_state.analysis = None
    st.session_state.quant = None
    st.session_state.master = None
    st.session_state.events = store.load_events()
    st.session_state.orderflow = None
    st.session_state.orderflow_frame = None
    st.session_state.cot = None
    st.session_state.cot_frame = None
    st.session_state.analysis_id = None
    st.session_state.ai_text = ''
    st.session_state.quality = None
    st.session_state.rss_items = pd.DataFrame()
    st.session_state.rss_triage = pd.DataFrame()



with st.sidebar:
    st.header('1 · Datos de mercado')
    asset = st.selectbox(
        'Activo',
        ['XAUUSD', 'EURUSD', 'EURJPY', 'DXY', 'US10Y']
    )
    interval = st.selectbox(
        'Temporalidad',
        ['15m', '30m', '1h', '4h', '1d'],
        index=2
    )
    period = st.selectbox(
        'Periodo (Yahoo)',
        ['1mo', '3mo', '6mo', '1y', '2y', '5y'],
        index=3
    )
    source_choice = st.radio(
        'Proveedor',
        ['Twelve Data API', 'Yahoo Finance', 'Cargar CSV propio']
    )
    
    auto_refresh = False
    refresh_count = 0

    if source_choice == 'Twelve Data API':
        auto_refresh = st.checkbox(
            'Actualizar automáticamente cada 60 segundos',
            value=False
        )

        if auto_refresh:
            from streamlit_autorefresh import st_autorefresh
            refresh_count = st_autorefresh(
                interval=60_000,
                key='market_auto_refresh'
            )


    twelve_key = st.text_input(
        'API key Twelve Data',
        value=leer_secreto('TWELVEDATA_API_KEY'),
        type='password'
    )

    outputsize = st.slider(
        'Velas (Twelve Data)',
        100, 5000, 500, 100
    )

    uploaded = st.file_uploader(
        'CSV OHLC',
        type=['csv'],
        help='Columnas: timestamp, open, high, low, close; volume opcional.'
    )

    run = st.button(
        'Cargar y analizar',
        type='primary',
        use_container_width=True
    )

    st.divider()
    st.caption(
        'Las claves se leen desde la sesión o desde tu .env local. '
        'No compartas ese archivo.'
    )

    st.divider()
    st.subheader('Alertas de Telegram')

    if st.button('Enviar mensaje de prueba', use_container_width=True):
        exito, mensaje = enviar_mensaje_telegram(
            'Combinación Maestra: conexión con Telegram comprobada. '
            'Este es un mensaje de prueba; no se ha ejecutado ninguna operación.'
        )

        if exito:
            st.success(mensaje)
        else:
            st.error(mensaje)
    if st.button('Diagnosticar Telegram', use_container_width=True):
        st.info(diagnosticar_telegram())


refresh_due = (
    auto_refresh
    and refresh_count > 0
    and refresh_count != st.session_state.get(
        '_last_refresh_count', 0
    )
)

if run or refresh_due:
    if refresh_due:
        st.session_state['_last_refresh_count'] = refresh_count

    try:
        if source_choice == 'Cargar CSV propio':
            if uploaded is None:
                st.error('Selecciona un CSV OHLC primero.')
                st.stop()

            df = normalize_ohlc(pd.read_csv(uploaded))
            meta = {
                'provider': 'CSV aportado por usuario',
                'provider_symbol': 'custom',
                'requested_asset': asset,
                'rows': len(df),
                'latest_timestamp_utc': str(df.timestamp.iloc[-1]),
                'proxy_note': 'La procedencia, calidad y licencia dependen del archivo cargado.'
            }

        elif source_choice == 'Twelve Data API':
            df, meta = download_twelvedata(
                asset, twelve_key, interval, outputsize
            )

        else:
            df, meta = download_yahoo(asset, period, interval)

        featured, market = analyze_market(df)
        quant = summarize_returns(df)
        quality = assess_ohlc_quality(df, interval=interval)

        store.save_bars(
            asset,
            interval,
            df,
            str(meta.get('provider', 'unknown'))
        )

        st.session_state.df = featured
        st.session_state.metadata = meta
        st.session_state.quality = quality
        st.session_state.analysis = market
        st.session_state.quant = quant

        st.session_state.master = combine(
            market,
            quant=quant,
            events=st.session_state.events.to_dict('records'),
            orderflow=st.session_state.orderflow,
            data_quality={
                'rows': len(df),
                'provider': meta.get('provider'),
                'quality': quality
            },
            news_items=(
                st.session_state.get(
                    'rss_triage', pd.DataFrame()
                ).to_dict('records')
                if not st.session_state.get(
                    'rss_triage', pd.DataFrame()
                ).empty
                else []
            )
        )

        if run:
            st.session_state.analysis_id = store.save_analysis(
                asset,
                interval,
                str(meta.get('provider', 'unknown')),
                meta,
                market,
                quant,
                st.session_state.master,
                st.session_state.ai_text
            )

        store.source_check(
            str(meta.get('provider', 'unknown')),
            'ok',
            f'{len(df)} velas; último timestamp '
            f'{meta.get("latest_timestamp_utc")}'
        )

        st.success(
            f'Análisis actualizado. Última vela: '
            f'{meta.get("latest_timestamp_utc")}'
        )

    
    except Exception as exc:
        store.source_check(
            source_choice, 'error', str(exc)
        )
        st.error(f'Error al cargar o analizar los datos: {exc}')


# Las pestañas deben estar fuera del bloque try/except.
market_tab, master_tab, macro_tab, flow_tab, cot_tab, quant_tab, news_tab, ai_tab, history_tab, sources_tab = st.tabs([
    'Mercado',
    'Motor maestro',
    'Macro y geopolítica',
    'Order Flow',
    'COT',
    'Laboratorio cuantitativo',
    'Noticias',
    'Análisis IA',
    'Historial',
    'Fuentes y calidad'
])

with market_tab:

with market_tab:
    st.subheader('Inteligencia interna del mercado')
    if st.session_state.df is None:
        st.info('Carga datos desde la barra lateral o usa el CSV de ejemplo de la carpeta data/.')
    else:
        df, market, quant, meta = st.session_state.df, st.session_state.analysis, st.session_state.quant, st.session_state.metadata
        cols = st.columns(5)
        cols[0].metric('Último cierre', f"{market['last_close']:,.4f}")
        cols[1].metric('Tendencia', market['trend'])
        cols[2].metric('Momentum 20 velas', f"{market['momentum_20_bars']*100:.2f}%")
        cols[3].metric('RSI 14', f"{market['rsi14']:.1f}" if market['rsi14'] is not None else 'N/D')
        cols[4].metric('ATR %', f"{market['atr_pct']*100:.2f}%" if market.get('atr_pct') is not None else 'N/D')
        chart = go.Figure(data=[go.Candlestick(x=df.timestamp, open=df.open, high=df.high, low=df.low, close=df.close, name='OHLC')])
        chart.add_trace(go.Scatter(x=df.timestamp, y=df.ema20, name='EMA20', line=dict(width=1)))
        chart.add_trace(go.Scatter(x=df.timestamp, y=df.ema50, name='EMA50', line=dict(width=1)))
        chart.update_layout(height=500, xaxis_rangeslider_visible=False, title=f"{asset} · {meta.get('provider_symbol','')} · {interval}")
        st.plotly_chart(chart, use_container_width=True)
        st.subheader('Estado técnico estructurado')
        st.json(market)
        st.caption('Estos indicadores se calculan desde OHLC. No son observación directa de liquidez ni Order Flow institucional.')

with master_tab:
    st.subheader('Motor de combinación maestra')
    if st.session_state.analysis is None:
        st.info('Carga primero un historial de mercado para construir la lectura integrada.')
    else:
        master = combine(st.session_state.analysis, quant=st.session_state.quant, events=st.session_state.events.to_dict('records'), orderflow=st.session_state.orderflow,
                         positioning=st.session_state.cot, data_quality={'rows':len(st.session_state.df),'provider':st.session_state.metadata.get('provider'),'quality':st.session_state.get('quality')}, news_items=st.session_state.get('rss_triage', pd.DataFrame()).to_dict('records') if not st.session_state.get('rss_triage', pd.DataFrame()).empty else [])
        st.session_state.master = master
        st.subheader(master['overall_reading'])
        st.metric('Puntuación heurística (no probabilidad)', master['heuristic_score'])
        st.json(master['score_components'])
        if master['contradictions']:
            st.warning('Contradicciones detectadas: ' + '; '.join(master['contradictions']))
        else:
            st.info('No se detectan contradicciones explícitas con los módulos actualmente disponibles; esto no implica certeza.')
        st.subheader('Escenarios condicionales')
        for scenario in master['scenarios']:
            with st.expander(scenario['name']):
                st.write('Condición:', scenario['condition'])
                st.write('Invalidación:', scenario['invalidates'])
        st.subheader('Limitaciones activas')
        for item in master['limitations']: st.write('• ' + item)
        report = {'analysis_id':st.session_state.analysis_id,'asset':asset,'metadata':st.session_state.metadata,'data_quality':st.session_state.get('quality'),'market':st.session_state.analysis,'quant':st.session_state.quant,'master':master,'orderflow':st.session_state.orderflow,'positioning':st.session_state.cot,'news':st.session_state.get('rss_items',pd.DataFrame()).to_dict('records') if not st.session_state.get('rss_items',pd.DataFrame()).empty else []}
        st.download_button('Exportar informe JSON', json.dumps(report, indent=2, ensure_ascii=False, default=str), file_name=f'informe_{asset}.json', mime='application/json')
        if st.button('Guardar nueva instantánea de esta lectura'):
            new_id = store.save_analysis(asset, interval, str(st.session_state.metadata.get('provider','unknown')), st.session_state.metadata, st.session_state.analysis, st.session_state.quant, master, st.session_state.ai_text)
            st.success(f'Instantánea guardada: ID {new_id}')

with macro_tab:
    st.subheader('Registro persistente de eventos macroeconómicos y geopolíticos')
    st.caption('Introduce solo eventos cuya fuente puedas revisar. La aplicación no verifica de forma independiente los hechos.')
    with st.form('event_form', clear_on_submit=True):
        event_date = st.date_input('Fecha del evento', value=date.today())
        title = st.text_input('Título / evento')
        category = st.selectbox('Categoría', ['Banco central','Inflación','Empleo','Geopolítica','Riesgo financiero','Oferta/demanda','Otro'])
        source = st.text_input('Fuente / organismo')
        source_url = st.text_input('URL original')
        channel = st.text_input('Canal de impacto (dólar, tipos reales, riesgo, oferta/demanda...)')
        bias = st.selectbox('Hipótesis de sesgo para oro', ['unknown','bullish','bearish','mixed'])
        confidence = st.slider('Confianza en la clasificación (subjetiva)', 0.0, 1.0, .5, .05)
        notes = st.text_area('Notas / evidencia')
        submitted = st.form_submit_button('Guardar evento')
    if submitted:
        if not title.strip(): st.error('El título del evento es obligatorio.')
        else:
            event = {'date_utc':pd.Timestamp(event_date,tz='UTC').isoformat(),'title':title,'category':category,'source':source,'source_url':source_url,'impact_channel':channel,'bias_gold':bias,'confidence':confidence,'notes':notes}
            store.save_event(event)
            st.session_state.events = store.load_events()
            st.success('Evento guardado en SQLite; estará disponible tras reiniciar la aplicación.')
    if not st.session_state.events.empty:
        st.dataframe(st.session_state.events, use_container_width=True, hide_index=True)
        st.download_button('Exportar eventos CSV', st.session_state.events.to_csv(index=False).encode(), 'eventos.csv', 'text/csv')
    else: st.info('No hay eventos guardados.')
    st.divider()
    st.subheader('Serie económica FRED')
    fred_id = st.text_input('ID de serie', 'DGS10')
    fred_key = st.text_input('API key FRED', os.getenv('FRED_API_KEY',''), type='password')
    if st.button('Consultar FRED'):
        try:
            fred = fetch_fred_series(fred_id, fred_key)
            st.session_state['fred_data'] = fred
            store.source_check('FRED:'+fred_id,'ok',f'{len(fred)} observaciones')
        except Exception as exc:
            store.source_check('FRED:'+fred_id,'error',str(exc)); st.error(str(exc))
    if not st.session_state.get('fred_data',pd.DataFrame()).empty:
        fred = st.session_state['fred_data']; st.line_chart(fred.set_index('date')['value']); st.dataframe(fred.tail(20), use_container_width=True)

with flow_tab:
    st.subheader('Order Flow desde archivo de operaciones/ticks')
    st.warning('Solo se calcula delta cuando el archivo contiene side o bid/ask. Velas OHLC por sí solas no permiten calcular un delta real.')
    tick_file = st.file_uploader('Subir CSV de ticks/trades', type=['csv'], key='tick_csv')
    if tick_file is not None and st.button('Analizar ticks / Order Flow'):
        try:
            flow_df, flow_summary = analyze_trades(pd.read_csv(tick_file))
            st.session_state.orderflow_frame, st.session_state.orderflow = flow_df, flow_summary
            store.source_check('CSV Order Flow','ok',json.dumps(flow_summary,default=str))
            st.success('Archivo procesado. El resumen se incorporará al motor maestro.')
        except Exception as exc:
            store.source_check('CSV Order Flow','error',str(exc)); st.error(str(exc))
    if st.session_state.orderflow:
        st.json(st.session_state.orderflow)
        st.line_chart(st.session_state.orderflow_frame.set_index('minute')[['signed_delta']])
        st.dataframe(st.session_state.orderflow_frame.tail(100), use_container_width=True)
        st.download_button('Exportar resumen Order Flow JSON', json.dumps(st.session_state.orderflow,indent=2,ensure_ascii=False), 'orderflow_resumen.json', 'application/json')
    st.markdown('**Formato de CSV esperado**: `timestamp,price,volume,side` (side = buy/sell), o `timestamp,price,volume,bid,ask`. Incluye proveedor y contrato en el nombre/notas para no mezclar feeds.')

with cot_tab:
    st.subheader('Posicionamiento de futuros — CFTC COT')
    st.write('Descarga un CSV del portal oficial CFTC y cárgalo aquí. Los informes son semanales y no son Order Flow intradía.')
    st.markdown('[Portal oficial CFTC Commitments of Traders](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm)')
    report_name = st.selectbox('Informe COT', list(CFTC_DATASETS.keys()), index=0)
    contract_search = st.text_input('Texto para filtrar contrato', 'GOLD')
    cot_limit = st.slider('Máximo de filas recientes a consultar', 50, 1000, 300, 50)
    if st.button('Consultar CFTC automáticamente (sin API key)'):
        try:
            raw_cot = fetch_cot_api(CFTC_DATASETS[report_name], contract_search, cot_limit)
            cot_frame, cot_summary = analyze_cot_csv(raw_cot, contract_search)
            cot_summary['source'] = 'CFTC Public Reporting Environment API'
            cot_summary['report'] = report_name
            st.session_state.cot_frame, st.session_state.cot = cot_frame, cot_summary
            store.source_check('CFTC API','ok',json.dumps(cot_summary,default=str))
            st.success('COT actualizado desde la API pública de CFTC.')
        except Exception as exc:
            store.source_check('CFTC API','error',str(exc)); st.error(str(exc))
    st.caption('Si la API pública falla o cambia su disponibilidad, descarga el CSV desde el portal oficial y usa el importador manual.')
    cot_file = st.file_uploader('O subir CSV COT', type=['csv'], key='cot_csv')
    if cot_file is not None and st.button('Analizar COT cargado'):
        try:
            cot_frame, cot_summary = analyze_cot_csv(pd.read_csv(cot_file), contract_search)
            st.session_state.cot_frame, st.session_state.cot = cot_frame, cot_summary
            store.source_check('CFTC COT CSV','ok',json.dumps(cot_summary,default=str))
            st.success('COT procesado.')
        except Exception as exc:
            store.source_check('CFTC COT CSV','error',str(exc)); st.error(str(exc))
    if st.session_state.cot:
        st.json(st.session_state.cot)
        st.dataframe(st.session_state.cot_frame.tail(100), use_container_width=True)
        st.download_button('Exportar COT filtrado', st.session_state.cot_frame.to_csv(index=False).encode(), 'cot_filtrado.csv', 'text/csv')

with quant_tab:
    st.subheader('Laboratorio cuantitativo')
    if st.session_state.df is None:
        st.info('Carga primero los datos OHLC.')
    else:
        df = st.session_state.df
        st.write('Estadísticas de retornos'); st.json(st.session_state.quant)
        horizon = st.slider('Horizonte bootstrap (velas)', 1, 100, 10)
        sims = st.select_slider('Simulaciones bootstrap', options=[500,1000,2000,5000,10000], value=2000)
        if st.button('Ejecutar bootstrap'):
            try: st.session_state['bootstrap_result'] = bootstrap_terminal_returns(df,horizon=horizon,simulations=sims)
            except Exception as exc: st.error(str(exc))
        if st.session_state.get('bootstrap_result'): st.json(st.session_state['bootstrap_result'])
        st.subheader('Validación cronológica de baseline')
        valid_horizon = st.slider('Horizonte para test fuera de muestra (velas)', 1, 20, 1)
        if st.button('Evaluar baseline momentum'):
            try: st.session_state['validation_result'] = evaluate_momentum_baseline(df, horizon=valid_horizon)
            except Exception as exc: st.error(str(exc))
        if st.session_state.get('validation_result'): st.json(st.session_state['validation_result'])
        st.caption('Baseline exploratorio; no sustituye validación por ventanas, costes, slippage, selección múltiple ni calibración con más muestras.')
    st.divider()
    st.subheader('Simulación multiagente estilizada (experimental)')
    st.caption('Simula seguidores de tendencia, reversión a la media y un shock hipotético. No se calibra con participantes reales y no pronostica el mercado.')
    c1,c2,c3 = st.columns(3)
    with c1: sim_steps = st.slider('Pasos',10,500,120)
    with c2: sim_n = st.select_slider('Trayectorias',options=[100,500,1000,5000,10000],value=1000)
    with c3: trend_strength = st.slider('Fuerza tendencia sintética',-3.0,3.0,0.0,.1)
    macro_shock = st.slider('Shock sintético',-5.0,5.0,0.0,.25)
    reversion = st.slider('Reversión a la media',0.0,1.0,.15,.05)
    if st.button('Ejecutar stress test sintético'):
        try: st.session_state['agent_result'] = simulate_agents(sim_steps,sim_n,trend_strength,macro_shock,reversion)
        except Exception as exc: st.error(str(exc))
    if st.session_state.get('agent_result'): st.json(st.session_state['agent_result'])

with news_tab:
    st.subheader('Noticias RSS y clasificación inicial')
    st.caption('El RSS solo aporta titulares/texto de la fuente. La clasificación por palabras clave es un filtro de triage, no verificación ni análisis causal definitivo.')
    rss_text = st.text_area('URLs RSS/Atom, una por línea', 'https://www.federalreserve.gov/feeds/press_all.xml', height=100)
    if st.button('Consultar fuentes RSS'):
        try:
            rss = fetch_rss([x.strip() for x in rss_text.splitlines() if x.strip()])
            st.session_state['rss_items'] = rss
            store.source_check('RSS','ok',f'{len(rss)} elementos')
        except Exception as exc:
            store.source_check('RSS','error',str(exc)); st.error(str(exc))
    rss = st.session_state.get('rss_items',pd.DataFrame())
    if not rss.empty:
        triage = classify_headlines(rss)
        st.session_state['rss_triage'] = triage
        st.dataframe(triage, use_container_width=True, hide_index=True)
        st.download_button('Exportar noticias clasificadas CSV', triage.to_csv(index=False).encode(), 'noticias_clasificadas.csv', 'text/csv')

with ai_tab:
    st.subheader('IA opcional: explicación, no fuente de verdad')
    st.caption('El contenido que envíes sale de tu equipo hacia el proveedor de IA. Revisa sus condiciones y evita datos sensibles.')
    ai_provider = st.selectbox('Proveedor', ['Gemini','OpenAI-compatible (Groq, OpenRouter u otro)'])
    ai_key = st.text_input('API key IA', value=os.getenv('GEMINI_API_KEY','') if ai_provider=='Gemini' else os.getenv('LLM_API_KEY',''), type='password')
    if ai_provider == 'Gemini':
        ai_model = st.text_input('Modelo', os.getenv('GEMINI_MODEL','gemini-2.5-flash')); ai_base = ''
    else:
        ai_model = st.text_input('Nombre de modelo exacto', os.getenv('LLM_MODEL','llama-3.3-70b-versatile'))
        ai_base = st.text_input('Base URL compatible', os.getenv('LLM_BASE_URL','https://api.groq.com/openai/v1'))
    if st.button('Generar lectura narrativa con IA', type='primary'):
        if st.session_state.analysis is None: st.error('Carga primero datos de mercado.')
        else:
            context = {'asset':asset,'metadata':st.session_state.metadata,'market_analysis':st.session_state.analysis,'quantitative_summary':st.session_state.quant,'master_reading':st.session_state.master,'events':st.session_state.events.tail(30).to_dict('records'),'orderflow':st.session_state.orderflow,'positioning':st.session_state.cot,'rss_headlines':st.session_state.get('rss_items',pd.DataFrame()).head(30).to_dict('records') if not st.session_state.get('rss_items',pd.DataFrame()).empty else []}
            try:
                st.session_state.ai_text = analyze_with_ai('gemini' if ai_provider=='Gemini' else 'openai-compatible',ai_key,ai_model,context,ai_base)
                store.source_check('IA:'+ai_provider,'ok',f'model={ai_model}')
                st.success('Análisis narrativo generado. Contrasta las afirmaciones con datos y fuentes originales.')
            except Exception as exc:
                store.source_check('IA:'+ai_provider,'error',str(exc)); st.error(str(exc))
    if st.session_state.ai_text:
        st.markdown(st.session_state.ai_text)
        st.download_button('Descargar texto IA', st.session_state.ai_text, f'analisis_ia_{asset}.txt', 'text/plain')

with history_tab:
    st.subheader('Historial local de análisis')
    hist = store.recent_analyses(200)
    if hist.empty: st.info('Todavía no hay análisis guardados. Cada carga exitosa crea una instantánea.')
    else:
        st.dataframe(hist[['id','created_at','asset','timeframe','provider']], use_container_width=True, hide_index=True)
        selected_id = st.selectbox('Elegir análisis para ver detalle', hist['id'].astype(int).tolist())
        selected = hist.loc[hist.id==selected_id].iloc[0]
        with st.expander('Detalle de la instantánea', expanded=True):
            st.json({'metadata':json.loads(selected.metadata_json),'market':json.loads(selected.market_json),'quant':json.loads(selected.quant_json),'master':json.loads(selected.master_json)})
        st.subheader('Registrar evaluación posterior manual')
        market_saved = json.loads(selected.market_json); master_saved = json.loads(selected.master_json)
        entry = float(market_saved.get('last_close',0) or 0)
        st.write(f"Precio de referencia guardado: {entry}")
        future_price = st.number_input('Precio observado después del horizonte', min_value=0.0, value=entry if entry>0 else 1.0, format='%.6f')
        eval_horizon = st.number_input('Horizonte transcurrido (velas)', min_value=1, max_value=10000, value=4)
        eval_notes = st.text_input('Notas de evaluación')
        if st.button('Guardar evaluación del escenario'):
            realized = future_price / entry - 1 if entry>0 else 0.0
            predicted = str(master_saved.get('overall_reading','neutral'))
            outcome = 'acierto direccional' if (('alcista' in predicted and realized>0) or ('bajista' in predicted and realized<0)) else 'no acierto direccional / neutral'
            store.save_evaluation(analysis_id=int(selected_id),asset=str(selected.asset),horizon_bars=int(eval_horizon),entry_price=entry,future_price=float(future_price),realized_return=float(realized),predicted_bias=predicted,outcome=outcome,notes=eval_notes)
            st.success('Evaluación guardada.')
    ev = store.evaluations()
    st.subheader('Evaluaciones guardadas')
    if not ev.empty:
        st.dataframe(ev, use_container_width=True, hide_index=True)
        st.download_button('Exportar evaluaciones CSV', ev.to_csv(index=False).encode(), 'evaluaciones.csv', 'text/csv')
    else: st.info('No hay evaluaciones todavía. La evaluación manual no sustituye una validación automática por horizonte.')

with sources_tab:
    st.subheader('Estado y procedencia de datos')
    if st.session_state.df is not None:
        df, meta = st.session_state.df, st.session_state.metadata
        st.json(meta)
        quality = st.session_state.get('quality') or assess_ohlc_quality(df, interval=interval)
        st.subheader('Control de calidad y frescura')
        st.metric('Índice de calidad (heurístico)', f"{quality.get('score', 0)}/100", delta=quality.get('status','sin estado'))
        st.json(quality)
        if quality.get('issues'):
            st.warning('Revisa estas observaciones antes de confiar en el análisis: ' + ' · '.join(quality['issues']))
        st.write({'rows':len(df),'start_utc':str(df.timestamp.iloc[0]),'end_utc':str(df.timestamp.iloc[-1]),'timestamps_unique':bool(df.timestamp.is_unique),'missing_ohlc':int(df[['open','high','low','close']].isna().sum().sum()),'nonpositive_prices':int((df[['open','high','low','close']]<=0).sum().sum())})
        st.dataframe(df.tail(100), use_container_width=True)
        st.download_button('Descargar OHLC CSV', df.to_csv(index=False).encode(), f'{asset}_ohlc.csv', 'text/csv')
    st.subheader('Historial de comprobaciones de fuentes')
    status = store.source_history()
    if not status.empty: st.dataframe(status, use_container_width=True, hide_index=True)
    st.subheader('Base de datos local')
    st.write(f'Ruta: `{(APP_DIR / "data" / "combinacion_maestra.sqlite3").resolve()}`')
    st.caption('La base de datos queda en tu ordenador. Haz copias de seguridad del archivo SQLite si quieres conservar historial; no incluyas claves API en las copias que compartas.')
    st.markdown('**Fuentes de referencia:** [Twelve Data](https://twelvedata.com/docs), [FRED API](https://fred.stlouisfed.org/docs/api/fred/), [CFTC COT](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm).')
