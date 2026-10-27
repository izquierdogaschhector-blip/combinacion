# CHANGELOG

## V6.0 — Diagnóstico de calidad e integración contextual de noticias
- Añadido `quality.py`: diagnóstico OHLC con tamaño de muestra, timestamps inválidos/duplicados, orden temporal, huecos y frescura aproximada.
- El dashboard muestra el índice heurístico de calidad y advertencias; el informe JSON conserva el resultado.
- Las noticias RSS clasificadas se incluyen como contexto temático en el motor maestro, pero no alteran automáticamente la puntuación direccional.
- Añadidas pruebas para calidad de datos y neutralidad direccional de titulares: 18 pruebas automáticas pasan.
- Documentación explícita sobre tareas que requieren claves, cuentas o proveedores externos.

## V5.0 — Persistencia, Order Flow importado y validación
- Añadida base de datos SQLite local para velas, eventos, instantáneas, evaluaciones y estado de fuentes.
- Añadido módulo de importación de operaciones/ticks; delta requiere `side` o `bid`/`ask`.
- Añadida consulta CFTC COT y alternativa CSV.
- Añadido triage de titulares RSS, evaluación cronológica y simulación multiagente estilizada.

## Límites conocidos
- No se ha verificado conexión real a APIs con credenciales del usuario.
- No incluye feed institucional de ticks/Level 2.
- COT automático depende de la disponibilidad/esquema del servicio público; CSV manual de respaldo.
- El triage de noticias no verifica hechos ni estima causalidad.
- Las puntuaciones no son probabilidades calibradas y no hay ejecución automática de órdenes.
