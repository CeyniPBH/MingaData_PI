# Auditoría de mensajes del tablero (dashboard)

Este documento recopila los mensajes, callouts, advertencias y estados que muestra el tablero Streamlit, organizados por pantalla, con su condición de aparición, severidad y propósito. Sirve para revisar que toda comunicación al usuario sea clara, honesta sobre las limitaciones de los datos y consistente.

## Pantalla 0 — Resumen (landing)

| Mensaje | Condición | Severidad | Propósito |
|---|---|---|---|
| KPIs de productos, municipios, horizonte, años de historial | Siempre | Informativo | Contexto inicial |
| Exposición sin modelo vs con modelo (t·min, COP) | Cuando hay métrica de negocio | Informativo | Valor del modelo de negocio |
| Callout de alcance: planificación, no trading ni precios | Siempre | Informativo | Límites del alcance |
| Tarjetas de navegación a pantallas de detalle | Siempre | Informativo | Navegación principal |
| "Resumen descargable en CSV" | Cuando se genera | Informativo | Exportación |

## Pantalla 1 — Oferta

| Mensaje | Condición | Severidad | Propósito |
|---|---|---|---|
| "No hay datos de oferta para {producto} en el año {año}" | Municipio sin oferta para el producto/año | Advertencia | Evitar interpretar vacío como cero |
| Tabla de pronóstico bajo/base/alto | Siempre que hay datos | Informativo | Valores numéricos de referencia |
| Serie histórica reciente (últimos 10 años) | Cuando hay histórico | Informativo | Contexto de la serie |
| Cobertura de intervalos ~76 % (nominal 80 %) | Nota implícita en docs | Informativo | Calibración de escenarios |

## Pantalla 2 — Zonas

| Mensaje | Condición | Severidad | Propósito |
|---|---|---|---|
| "No hay datos para {producto} en {año}" | Filtro sin resultados | Advertencia | Evitar mapa vacío sin explicación |
| Resumen por municipio ordenado | Siempre que hay datos | Informativo | Ranking de oferta |
| Métricas: oferta total, promedio, municipios con producción | Siempre que hay datos | Informativo | Agregados rápidos |

## Pantalla 2b — Zonas de acopio

| Mensaje | Condición | Severidad | Propósito |
|---|---|---|---|
| "No se encontró data/results/zonas.csv. Corre: python src/arendonc2/zonas_acopio.py" | Archivo faltante | Error | Indicar cómo generar el insumo |
| "Cobertura parcial de consumo: {x}% ..." | Cobertura < 100 % | Advertencia | Productos sin excedente definido quedan excluidos de la optimización |
| "Los centros de zona son referencias, no la ubicación óptima" | Siempre | Informativo | Diferenciar de pantalla 3 |

## Pantalla 3 — Ubicación

| Mensaje | Condición | Severidad | Propósito |
|---|---|---|---|
| "Matriz de tiempos inválida: {e}" | Matriz corrupta | Error | Bloquear cálculo con datos inválidos |
| "No se pudo cargar el escenario {id}: {e}" | Escenario faltante | Error | Indicar cómo generar escenarios |
| "Cobertura parcial: {x}% ... productos sin equivalencia de unidad ..." | Cobertura < 100 % | Advertencia | Volumen conocido parcial |
| "La optimización se ejecuta sólo al pulsar el botón" | Siempre | Informativo | Setear expectativa de cálculo bajo demanda |
| "Ajusta los parámetros y pulsa Calcular optimización" | Cambio de parámetros sin calcular | Informativo | Guiar al usuario |
| "El solver no encontró solución (estado: {estado})" | Solver falla | Error | Informar estado real del solver |
| "Solución factible (no certificada óptima dentro del límite/brecha)" | status == FEASIBLE | Advertencia | No presentar como óptima |
| "Ubicación estable: la misma central en todos los niveles de oferta" | Estabilidad, una central | Éxito | Resultado de robustez |
| "Ubicación variable: la central cambia según el nivel de oferta" | Estabilidad, varias centrales | Advertencia | Resultado de robustez |
| "La versión base no impone capacidad mínima ni máxima por acopio" | Siempre | Informativo | Supuesto del modelo |
| "Capacidades: se usan 5 satélites" | Siempre | Informativo | Parámetro fijo |
| "El límite de tiempo NO se reduce por defecto para aparentar velocidad" | Expander solver | Informativo | Honestidad sobre el solver |

## Pantalla 4 — Cobertura y capacidad

| Mensaje | Condición | Severidad | Propósito |
|---|---|---|---|
| "No se encontro el tablero en {ruta}" | HTML faltante | Error | Indicar archivo ausente |
| "No se pudo cargar el tablero central: {e}" | Error de lectura | Error | Informar falla de carga |
| "Vista de cobertura ... No reemplaza la pantalla 3 ..." | Siempre | Informativo | Diferenciar pantallas 3 y 4 |
| "El indicador 'recuperable' es una referencia del análisis original y no se recalcula desde el CSV" | Siempre | Informativo | Limitación del dato embebido |

## Pie de página (todas las pantallas)

| Mensaje | Condición | Severidad | Propósito |
|---|---|---|---|
| Créditos de autores y fuentes de datos | Siempre | Informativo | Atribución y trazabilidad |

## Principios de redacción auditados

1. **Honestidad:** los mensajes de error y advertencia no ocultan limitaciones (matriz aproximada, cobertura parcial, solver factible vs óptimo).
2. **Consistencia:** los títulos conservan las cadenas exigidas (`Pantalla 1 - Oferta`, `Pantalla 2 - Zonas`, `Pantalla 3 - Ubicacion`).
3. **Unidades:** cada métrica numérica lleva su unidad (t, t·min, COP, %).
4. **Acción:** los mensajes de error incluyen qué hacer (corregir archivo, ejecutar script).
