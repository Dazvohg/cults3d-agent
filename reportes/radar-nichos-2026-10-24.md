# Radar de nichos – 24/10/2026

Respuesta a: cómo hacer que el análisis traiga cosas más acordes y cree mejor.

## Problema
analizador_v2 trae el top 500 pagos por descargas (creationsBatch sort BY_DOWNLOADS, últimos 90 días). Ese muestreo no contiene los nichos donde sí vendimos: probado en modo offline, términos como radiation shield, weather station, bme280, sht31, esp32 dan 0 resultados en la muestra.

## Solución (tools/radar_nichos.py + specs/semillas_nichos.txt)
- Consulta por término (semillas editables + tags de lo que ya vendió) y mide demanda (vistas/día mediana de los 20 orgánicos mejor posicionados), competencia (nº de orgánicos) y oportunidad = demanda / (1 + competencia/10). Excluye IP, Art y conversión >20 %.
- Antes de buscar, consulta el esquema real de la API (creationsBatch args y valores de sort) y lo guarda en reportes/schema_creationsBatch.json. Si la API no expone búsqueda por texto, cae a modo offline y lo avisa.
- Corre en semanal.yml (paso 1c, continue-on-error). Salida: reportes/radar_nichos.md y .csv.

## Límites
- Sin acceso a cults3d.com desde el sandbox: la búsqueda por texto en la API no está probada; el primer run real confirma o no.
- La API no da volumen de búsquedas: vistas/día de los resultados mejor posicionados es un proxy.

## Bucle de mejora
1. Lunes: leer radar_nichos.md, tomar APOSTAR con competencia baja.
2. Diseñar 1-2 piezas por nicho con ficha técnica (compatibilidad, medidas, qué incluir).
3. Medir vistas por ficha cada semana (snapshot pendiente en ventas.py) y descartar nichos sin tracción a las 4 semanas.
