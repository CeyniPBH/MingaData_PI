# Métrica de negocio: impacto logístico en t·min y COP

## 1. Pregunta

¿Cuánto cambia la exposición logística si la recolección se planifica con el pronóstico en lugar de hacerlo sin modelo?

La métrica no es un costo contable. Es una **exposición bruta de planificación**: si la oferta real difiere de la estimada, esa diferencia debe moverse igual por la red. Se mide en **toneladas × minutos** (t·min) y se traduce a COP con un supuesto explícito.

## 2. Método

1. Se toma la oferta real y las predicciones walk-forward de 2019-2023.
2. Para cada municipio se calcula el tiempo al nodo logístico más cercano (central o satélite) de la red del escenario base de OR-Tools.
3. La exposición de una alternativa es `Σ |predicción − real| × minutos_al_nodo`.
4. Se compara contra cuatro alternativas:
   - **Sin modelo:** promedio de los últimos 5 años (`mean5`).
   - **Ingenuo:** último año observado (`naive`).
   - **Modelo final:** ensamble `(naive + LightGBM) / 2`.
   - **Modelo con compuerta:** usa el ensamble solo en los productos donde superó al ingenuo en 2022 y tienen volumen material; en el resto usa el ingenuo.
5. La compuerta se entrena en 2022 y se evalúa en 2023, que no participó en su selección.

### Red logística

Central: **Bugalagrande (76113)**. Satélites del escenario base: **76036, 76122, 76318 y 76670**. La lista de satélites del CSV incluye además el código de la central, por eso el conjunto único de nodos es de 5. El tiempo de cada municipio es el mínimo al conjunto.

### Supuesto de costo

| Supuesto | Valor |
|---|---:|
| Costo de operación del camión | 120.000 COP/hora |
| Capacidad del camión | 8 t |
| Costo por t·min | 120.000 / 60 / 8 = **250 COP/(t·min)** |
| Sensibilidad baja | 100 COP/(t·min) |
| Sensibilidad alta | 600 COP/(t·min) |

El costo es lineal: duplicar el costo por t·min duplica el impacto en COP. No incluye precio del producto, deterioro, capacidad real de flota ni costo de almacenamiento.

## 3. Resultado principal

### Horizonte 1, 2019-2023

| Alternativa | Error absoluto (t) | Exposición (M t·min) | COP base (miles de millones) | Δ vs sin modelo |
|---|---:|---:|---:|---:|
| Sin modelo | 14.414.547 | 729,06 | 182,26 | 0,00 % |
| Ingenuo | 8.447.452 | 419,65 | 104,91 | **−42,44 %** |
| Modelo final | 9.024.812 | 450,71 | 112,68 | **−38,18 %** |

### Validación 2022 y holdout 2023

| Ámbito | Alternativa | Exposición (M t·min) | COP base (miles de millones) | Δ vs sin modelo |
|---|---|---:|---:|---:|
| 2022 (validación) | Sin modelo | 176,72 | 44,18 | 0,00 % |
| 2022 | Ingenuo | 150,01 | 37,50 | −15,11 % |
| 2022 | Modelo final | 154,57 | 38,64 | −12,53 % |
| 2023 (holdout) | Sin modelo | 114,65 | 28,66 | 0,00 % |
| 2023 | Ingenuo | 86,17 | 21,54 | −24,85 % |
| 2023 | Modelo final | 88,83 | 22,21 | −22,52 % |
| 2023 | Modelo con compuerta | **86,16** | **21,54** | **−24,85 %** |

### Todos los horizontes

| Alternativa | Exposición (M t·min) | Δ vs sin modelo |
|---|---:|---:|
| Sin modelo | 2.843,67 | 0,00 % |
| Ingenuo | 1.843,76 | −35,16 % |
| Modelo final | 1.843,78 | −35,16 % |

**Lectura:** el modelo reduce la exposición entre 22,5 % y 38,2 % frente a no usar modelo. El ingenuo es ligeramente mejor en h=1; el ensamble se vuelve competitivo en horizontes largos. La compuerta recupera el desempeño del ingenuo en 2023 sin renunciar al modelo donde aporta.

## 4. Por horizonte

| Horizonte | Sin modelo (M t·min) | Ingenuo (M t·min) | Modelo (M t·min) | Modelo vs ingenuo |
|---:|---:|---:|---:|---:|
| 1 | 729,06 | 419,65 | 450,71 | −7,40 % |
| 2 | 733,86 | 471,81 | 489,46 | −3,74 % |
| 3 | 641,39 | 434,39 | 433,78 | +0,14 % |
| 4 | 481,21 | 337,21 | 310,67 | **+7,88 %** |
| 5 | 258,15 | 180,70 | 159,16 | **+11,92 %** |

**Lectura:** el modelo aporta en h=4 y h=5 (7,9 % y 11,9 % menos exposición que el ingenuo) y pierde en h=1 y h=2. Es consistente con el diagnóstico: el ensamble suaviza y acierta más a largo plazo, pero el ingenuo es difícil de vencer en el corto plazo.

## 5. Compuerta por producto

La compuerta selecciona un producto si en 2022 el ensamble mejora al ingenuo al menos 5 % en error absoluto **y** el volumen real es al menos 5.000 t.

| Producto | Volumen 2022 (t) | Mejora 2022 vs ingenuo | ¿Usa modelo? |
|---|---:|---:|---|
| Lulo | 16.817 | +5,74 % | **Sí** |
| Maracuyá | 11.026 | +7,41 % | **Sí** |
| Papaya | 15.284 | +11,06 % | **Sí** |
| Vid | 19.975 | +5,16 % | **Sí** |
| Cítricos | 176.464 | +3,90 % | No |
| Café | 37.094 | +3,44 % | No |
| Yuca | 7.330 | +4,79 % | No |
| Resto | — | < 5 % o volumen < 5.000 t | No |

En 2023 la compuerta usa el ensamble en esos 4 productos y el ingenuo en los demás. El resultado es 86,16 M t·min, prácticamente igual al ingenuo (86,17) y mejor que el ensamble puro (88,83). Es una estrategia conservadora: no promete una gran mejora, pero evita el deterioro del ensamble en los productos donde no aporta.

## 6. Por producto en 2023

| Producto | Exposición modelo (t·min) | Exposición ingenua (t·min) | Δ modelo vs ingenuo |
|---|---:|---:|---:|
| Vid | 14.732 | 27.625 | **−46,67 %** |
| Arracacha | 13.501 | 22.120 | **−38,97 %** |
| Mango | 24.207 | 30.982 | **−21,87 %** |
| Yuca | 125.502 | 145.141 | −13,53 % |
| Mora | 28.987 | 30.705 | −5,60 % |
| Lulo | 203.010 | 211.770 | −4,14 % |
| Cebolla Larga | 90.700 | 94.529 | −4,05 % |
| Plátano | 1.672.393 | 1.688.020 | −0,93 % |
| Maracuyá | 113.340 | 112.353 | +0,88 % |
| Café | 461.809 | 455.801 | +1,32 % |
| Caña de azúcar | 81.469.729 | 79.366.160 | +2,65 % |
| Aguacate | 676.815 | 652.538 | +3,72 % |
| Guayaba | 198.681 | 191.287 | +3,87 % |
| Ají | 71.232 | 67.516 | +5,50 % |
| Papaya | 183.592 | 173.520 | +5,80 % |
| Banano | 505.951 | 476.929 | +6,09 % |
| Piña | 1.491.857 | 1.387.367 | +7,53 % |
| Cítricos | 583.012 | 481.345 | +21,12 % |
| Caña panelera | 795.482 | 499.765 | +59,17 % |
| Sábila | 26.793 | 14.852 | +80,40 % |
| Borojó | 71.658 | 24.276 | +195,18 % |

**Lectura:** el modelo aporta mucho en Vid, Arracacha y Mango; pierde en caña panelera, sábila y borojó. La compuerta corrige la caña panelera (no la selecciona), pero no puede corregir productos que mejoraron en 2022 y fallaron en 2023 (Papaya). Es el riesgo de usar una sola ventana de validación.

## 7. Sensibilidad del costo

Impacto en 2023 (holdout), en miles de millones de COP:

| Alternativa | 100 COP/(t·min) | 250 COP/(t·min) | 600 COP/(t·min) |
|---|---:|---:|---:|
| Sin modelo | 11,47 | 28,66 | 68,79 |
| Ingenuo | 8,62 | 21,54 | 51,70 |
| Modelo final | 8,88 | 22,21 | 53,30 |
| Modelo con compuerta | 8,62 | 21,54 | 51,69 |

La conclusión no cambia con el supuesto: el orden de alternativas se mantiene. El valor absoluto sí cambia, por eso se reporta el rango y no un único COP.

## 8. Interpretación

- **El valor está en reducir la exposición, no en un ahorro contable.** La métrica compara alternativas bajo el mismo supuesto; no es una factura.
- **El ingenuo es un rival fuerte.** En datos anuales y series cortas, repetir el último año es difícil de superar. El modelo no debe venderse como una mejora universal.
- **El ensamble aporta a largo plazo.** h=4 y h=5 son los horizontes donde la planificación de capacidad importa; allí la mejora es clara.
- **La compuerta es una decisión de riesgo.** Usa el modelo solo donde hay evidencia previa y volumen; en 2023 iguala al ingenuo y evita el deterioro del ensamble puro.
- **La caña de azúcar domina el agregado.** Cualquier cambio en su pronóstico mueve el total; por eso se reporta por producto y por horizonte, no solo el total.

## 9. Limitaciones

- No incluye precio del producto, deterioro, merma ni costo de almacenamiento.
- No modela capacidad de flota ni rutas reales; usa tiempos al nodo más cercano.
- La matriz de tiempos es aproximada (línea recta × 1,4 / 45 km/h).
- La compuerta se calibró con una sola ventana (2022) y se evaluó con una sola (2023).
- El holdout es pequeño (571 observaciones) y está dominado por caña de azúcar.
- t·min es una proxy de exposición; no reemplaza un estudio logístico detallado.

## 10. Artefactos

| Artefacto | Ruta |
|---|---|
| Resumen | `data/results/ML_Ce/metrica_negocio_resumen.csv` |
| Por producto | `data/results/ML_Ce/metrica_negocio_producto.csv` |
| Por horizonte | `data/results/ML_Ce/metrica_negocio_horizonte.csv` |
| Compuerta | `data/results/ML_Ce/metrica_negocio_gate.csv` |
| Supuestos | `data/results/ML_Ce/metrica_negocio_supuestos.yaml` |
| Código | `src/ML_C/10_metrica_negocio.py` |
