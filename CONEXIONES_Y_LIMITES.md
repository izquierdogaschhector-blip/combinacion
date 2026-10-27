# Conexiones externas: qué puedo dejar programado y qué debes aportar tú

## Programado en el paquete
- Cliente REST de Twelve Data para velas OHLC, sujeto a símbolo/intervalo/plan.
- Alternativa Yahoo Finance y carga de CSV.
- Consulta FRED con API key opcional.
- CFTC COT público y carga CSV de respaldo.
- RSS/Atom con clasificación preliminar.
- IA opcional mediante Gemini o endpoint compatible con OpenAI API.
- Persistencia local, informe JSON, historial, diagnóstico de calidad y pruebas automáticas.

## Debes hacer tú
1. Instalar Python 3.11 o 3.12 y ejecutar el instalador.
2. Crear tus cuentas si hacen falta y pegar las claves en la aplicación local o en `.env`.
3. Verificar en la cuenta del proveedor el símbolo, frecuencia, histórico, límites de llamadas, retrasos y licencia.
4. Para Order Flow real, contratar/usar un feed que dé operaciones con clasificación buy/sell o bid/ask; para profundidad Level 2, el feed debe ofrecer explícitamente esa profundidad y derechos de uso.
5. Revisar las noticias originales y validar los resultados antes de confiar en cualquier lectura.

## Sobre datos gratuitos
- Twelve Data documenta el endpoint `/time_series`, pero la disponibilidad depende del símbolo y plan. No des por hecho que XAU/USD spot esté incluido en el plan gratuito.
- FRED requiere una clave para la API.
- CFTC publica datos COT, normalmente semanales; no son Order Flow intradía.
- APIs de IA gratuitas pueden tener cuotas, cambios de modelos, restricciones regionales o condiciones de uso de datos.

## Seguridad
- Nunca compartas `.env`, capturas con claves ni el archivo de base de datos si contiene información privada.
- `.env` está excluido de Git por `.gitignore`.
- El texto enviado a una API de IA sale de tu ordenador; revisa su política de privacidad.

## Límites del modelo
- El motor es basado en reglas; su puntuación es un sesgo heurístico, no una probabilidad.
- La simulación de agentes es hipotética, no una réplica de bancos o fondos.
- Un feed de futuros COMEX no representa el mercado OTC completo de XAUUSD spot.
- Ningún paquete puede garantizar cero fallos o resultados rentables.
