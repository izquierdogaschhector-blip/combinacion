# COMBINACIÓN MAESTRA V6.0

V6.0 · Plataforma local de investigación financiera que integra análisis OHLC, datos de Twelve Data/Yahoo/CSV, registro macro-geopolítico persistente, RSS con clasificación preliminar, Order Flow a partir de operaciones/ticks aportados, importación de COT de la CFTC, laboratorio cuantitativo, simulación sintética de agentes, análisis narrativo opcional con IA e historial SQLite.

> **Límites importantes:** no ejecuta operaciones, no es asesoramiento financiero, no garantiza resultados y no ofrece probabilidades predictivas calibradas. El sistema no fabrica un Order Flow si no hay datos de operaciones adecuados. Las cotizaciones y noticias pueden tener retrasos, errores o restricciones de licencia.

## Instalación rápida

### Windows
1. Instala Python 3.11 o 3.12 desde https://www.python.org/downloads/ y marca “Add Python to PATH”.
2. Descomprime el ZIP en una carpeta normal (no dentro del ZIP).
3. Haz doble clic en `INICIAR_WINDOWS.bat`.
4. La primera ejecución crea un entorno virtual e instala dependencias; después abre Streamlit en el navegador, normalmente `http://localhost:8501`.

### macOS / Linux
1. Instala Python 3.11 o 3.12.
2. En Terminal, entra en la carpeta descomprimida.
3. Ejecuta `chmod +x INICIAR_MAC_LINUX.sh` y luego `./INICIAR_MAC_LINUX.sh`.

### Instalación manual
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

## Configuración de APIs

Puedes introducir las claves en la interfaz o crear `.env` copiando `.env.example`. Reinicia la aplicación si cambias `.env`.

```dotenv
TWELVEDATA_API_KEY=PEGA_AQUI_TU_CLAVE
FRED_API_KEY=PEGA_AQUI_TU_CLAVE
GEMINI_API_KEY=PEGA_AQUI_TU_CLAVE
GEMINI_MODEL=gemini-2.5-flash
LLM_API_KEY=
LLM_MODEL=
LLM_BASE_URL=https://api.groq.com/openai/v1
```

No incluyas `.env` en un ZIP compartido ni subas el archivo a GitHub. Las claves no vienen incluidas. La IA es opcional; el resto del sistema funciona sin ella.

### Twelve Data
1. Crea una cuenta en https://twelvedata.com/ y copia tu API key.
2. Comprueba en tu cuenta que el plan cubra el activo, intervalo, historial y tipo de datos solicitado.
3. Selecciona `Twelve Data API` y pulsa `Cargar y analizar`.

Documentación: https://twelvedata.com/docs. El endpoint `/time_series` devuelve velas OHLC y volumen cuando esté disponible; la cobertura depende del símbolo y del plan. No presupongas que el nivel gratuito incluye oro spot en todos los casos.

### Yahoo Finance
Alternativa para datos de referencia. Para `XAUUSD` utiliza `GC=F` (futuros COMEX), **no oro spot**. Los símbolos FX también pueden diferir de la cotización de tu broker y el histórico intradía puede estar limitado.

### FRED
Solicita una clave en https://fred.stlouisfed.org/docs/api/api_key.html. Introduce el ID de serie (por ejemplo `DGS10`) en Macro/Geopolítica. La frecuencia y disponibilidad dependen de cada serie. Documentación: https://fred.stlouisfed.org/docs/api/fred/series_observations.html.

### IA opcional
- Gemini: https://aistudio.google.com/app/apikey. Nivel gratuito sujeto a modelo, región, límites y condiciones vigentes: https://ai.google.dev/gemini-api/docs/pricing.
- Proveedor compatible con OpenAI API: usa la URL base, el nombre de modelo y la clave que indique tu proveedor (por ejemplo, Groq u OpenRouter si sus condiciones lo permiten).
- El contenido enviado a una API de IA sale de tu equipo. Revisa privacidad, retención y condiciones del proveedor. No envíes datos sensibles.

## Novedades V6.0

- Control de calidad y frescura de las velas (índice heurístico, timestamps, duplicados y huecos).
- Titulares RSS integrados en el contexto del motor maestro, sin alterar automáticamente su sesgo direccional.
- Informe JSON incluye diagnóstico de calidad y titulares cargados.
- 18 pruebas automáticas locales.

## Módulos incluidos

1. **Inteligencia de mercado:** EMA20/50, RSI, ATR, momentum, extremos recientes y estadísticas descriptivas desde OHLC.
2. **Motor maestro:** integra tendencia, momentum, eventos clasificados por el usuario y, si se carga, delta de un feed de operaciones. Presenta contradicciones y escenarios condicionales. La puntuación no es probabilidad.
3. **Macro/geopolítica:** registro persistente de eventos, fuente, URL, canal de impacto, hipótesis de sesgo y confianza subjetiva. Consulta opcional de series FRED.
4. **Order Flow:** importa CSV de ticks/operaciones y calcula delta solo si hay `side` o `bid` y `ask`. Si faltan, el sistema se niega a inventarlo.
5. **COT/posicionamiento:** consulta la API pública de CFTC sin clave o importa un CSV manual; filtra contratos y calcula el neto del grupo de posicionamiento disponible si los campos existen.
6. **Laboratorio cuantitativo:** estadísticas, bootstrap, baseline temporal y evaluación cronológica de momentum.
7. **Simulación multiagente:** stress test estilizado de tendencia, reversión y shock. Es sintético, no calibrado y no pronostica el mercado.
8. **Noticias:** RSS/Atom y triage por palabras clave. Las etiquetas requieren revisión humana y no verifican veracidad ni impacto neto.
9. **IA opcional:** redacta una interpretación sobre los datos y titulares ya cargados; no es una fuente de cotizaciones ni una verificación de hechos.
10. **Historial:** guarda velas, eventos, instantáneas de análisis, evaluaciones manuales y estado de fuentes en SQLite local.

## Order Flow: formato CSV

Requiere `timestamp`, `price`, `volume` y una de estas opciones:

- `side` con valores `buy`/`sell` (también acepta `b`/`s`, `ask`/`bid`); o
- `bid` y `ask`, para una clasificación aproximada por precio de operación.

Ejemplo de columnas:
```csv
timestamp,price,volume,side
2026-01-01T10:00:00Z,4300.1,2.0,buy
2026-01-01T10:00:01Z,4300.0,1.0,sell
```

`data/ejemplo_ticks_sinteticos_NO_REAL.csv` es solo una muestra sintética para probar el importador. No usarla para análisis de mercado.

**Advertencia:** el delta calculado solo representa el feed/archivo cargado. XAUUSD spot es OTC y no tiene un libro de órdenes centralizado único. Un feed de futuros COMEX puede ser útil, pero no debe etiquetarse como flujo consolidado de spot.

## COT: cómo cargarlo

1. Abre el portal oficial: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm.
2. Descarga el CSV del informe que corresponda (por ejemplo, disaggregated o legacy; futures only o combined).
3. En la pestaña `COT / Posicionamiento`, carga el CSV y filtra por `GOLD` (o texto que aparezca en el nombre de contrato).
4. Comprueba el resumen y las columnas originales.

COT es semanal y corresponde a posicionamiento reportado de futuros/opciones; no es flujo intradía de spot.

## Historial y evaluación

Cada carga correcta guarda una instantánea en `data/combinacion_maestra.sqlite3`. En `Historial y evaluación` puedes consultar análisis anteriores y registrar manualmente un precio observado posterior. La evaluación manual no demuestra rentabilidad ni causalidad. Haz una copia de seguridad del archivo SQLite si quieres preservar el historial.

## Qué requiere el usuario

El paquete no puede crear cuentas externas ni generar tus claves. Debes introducir tú las API keys en la interfaz o en `.env`, instalar/ejecutar la aplicación en tu ordenador y aceptar los términos de cada proveedor. No pegues claves en este chat. Para Order Flow institucional automático necesitas contratar o configurar una fuente que proporcione los ticks/side/depth requeridos; Twelve Data OHLC por sí solo no proporciona un libro de órdenes completo del XAUUSD OTC.

## Validación

El baseline cronológico evita barajar datos, pero sigue siendo exploratorio. Para validar una estrategia real harían falta múltiples ventanas temporales, costes, spread, slippage, disponibilidad real del feed y control de selección múltiple. La puntuación maestra y los escenarios no son probabilidades calibradas.

## Pruebas automáticas

Desde la carpeta del proyecto:
```bash
pytest -q
```

Las pruebas son locales y usan datos simulados; no verifican credenciales ni disponibilidad de proveedores externos, y no consumen créditos API.

## Solución de problemas

- **API key / símbolo rechazado:** revisa plan, créditos, nombre de símbolo e intervalo en el proveedor.
- **Pocas velas:** cambia a 1h/4h/1d, amplía periodo si está disponible o importa CSV.
- **Order Flow no calculable:** comprueba que CSV tenga `timestamp`, `price`, `volume` y `side` o `bid`+`ask`.
- **COT no detecta GOLD:** abre el CSV y mira el nombre exacto de la columna de contrato; ajusta el texto de filtro.
- **Falla instalación:** utiliza Python 3.11/3.12 y ejecuta `pip install -r requirements.txt` en el entorno virtual.
- **IA falla:** verifica modelo exacto, endpoint, cuota y clave. El resto del sistema no depende de la IA.
- **Puerto ocupado:** ejecuta `streamlit run app.py --server.port 8502`.

## Qué no se afirma

- No se identifica a bancos/fondos ni se deduce su intención a partir de velas.
- No se crea Order Flow real a partir de OHLC.
- No se presenta COT semanal como señal intradía.
- No se presentan escenarios sintéticos como previsiones reales.
- No se promete una aplicación sin fallos ni una rentabilidad determinada.
