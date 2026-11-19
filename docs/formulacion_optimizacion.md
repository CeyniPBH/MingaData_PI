# Formulación del Problema de Ubicación de Central y Acopios Satélite

## 1. Pregunta de negocio

¿Dónde ubicar una central de acopio y procesamiento de productos agrícolas en el Valle del Cauca, y qué red de acopios satélite necesita, para minimizar el costo total de recoger la producción de los municipios y distribuir los productos a los mercados nacionales e internacionales?

## 2. Conjuntos e índices

| Símbolo | Descripción |
|---------|-------------|
| $M$ | Conjunto de municipios candidatos ($|M| = 42$ en el Valle del Cauca) |
| $S \subseteq M$ | Subconjunto de municipios candidatos para acopio satélite |
| $C \subseteq M$ | Subconjunto de municipios candidatos para central principal |
| $D$ | Conjunto de destinos de distribución: {Buenaventura, Aeropuerto Palmira, Cali, Bogotá, Medellín} |
| $P$ | Conjunto de productos agrícolas |
| $K$ | Número de acopios satélite a abrir (parámetro, $k \in [3, 8]$) |

## 3. Parámetros

| Parámetro | Descripción | Unidad |
|-----------|-------------|--------|
| $o_{p,m}$ | Oferta esperada del producto $p$ en el municipio $m$ | toneladas/año |
| $t^{rec}_{m,s}$ | Tiempo de viaje del municipio $m$ al acopio satélite $s$ | minutos |
| $t^{dist}_{c,d}$ | Tiempo de viaje de la central $c$ al destino $d$ | minutos |
| $\alpha_p$ | Proporción del producto $p$ que va a mercado nacional | [0,1] |
| $\beta_p$ | Proporción del producto $p$ que va a exportación | [0,1], $\alpha_p + \beta_p = 1$ |
| $f_c$ | Costo fijo de apertura de la central en municipio $c$ | COP/año |
| $f_s$ | Costo fijo de apertura de acopio satélite en municipio $s$ | COP/año |
| $k_{min}, k_{max}$ | Número mínimo y máximo de acopios satélite | unidades |
| $cap_{min}, cap_{max}$ | Capacidad mínima y máxima por acopio (si aplica) | toneladas/año |

## 4. Variables de decisión

| Variable | Tipo | Descripción |
|----------|------|-------------|
| $x_c \in \{0,1\}$ | Binaria | 1 si se abre la central en el municipio $c$ |
| $y_s \in \{0,1\}$ | Binaria | 1 si se abre un acopio satélite en el municipio $s$ |
| $z_{m,s} \in \{0,1\}$ | Binaria | 1 si el municipio $m$ asigna su producción al acopio satélite $s$ |
| $w_{s,c} \in \{0,1\}$ | Binaria | 1 si el acopio satélite $s$ asigna su volumen a la central $c$ |

**Restricción de unicidad:** Cada municipio se asigna a exactamente un acopio, y cada acopio se asigna a exactamente una central.

## 5. Función objetivo (multiobjetivo)

Se minimizan dos costos que compiten:

### Costo de recolección (municipio → acopio satélite)

$$Z_1 = \sum_{m \in M} \sum_{s \in S} \sum_{p \in P} o_{p,m} \cdot t^{rec}_{m,s} \cdot z_{m,s}$$

### Costo de distribución (central → destinos)

$$Z_2 = \sum_{c \in C} \sum_{d \in D} \sum_{p \in P} \left( \alpha_p \cdot o^{nac}_{p,c} + \beta_p \cdot o^{exp}_{p,c} \right) \cdot t^{dist}_{c,d} \cdot w_{s,c}$$

Donde $o^{nac}_{p,c}$ y $o^{exp}_{p,c}$ son los volúmenes del producto $p$ que llegan a la central $c$ con destino nacional y exportación respectivamente.

### Objetivo combinado (pesado)

$$Z = \lambda \cdot Z_1 + (1 - \lambda) \cdot Z_2, \quad \lambda \in [0, 1]$$

## 6. Restricciones

### R1: Abrir exactamente una central
$$\sum_{c \in C} x_c = 1$$

### R2: Abrir exactamente k acopios satélite
$$\sum_{s \in S} y_s = k$$

### R3: Cada municipio se asigna a un acopio abierto
$$\sum_{s \in S} z_{m,s} = 1, \quad \forall m \in M$$
$$z_{m,s} \leq y_s, \quad \forall m \in M, \forall s \in S$$

### R4: Cada acopio se asigna a una central abierta
$$\sum_{c \in C} w_{s,c} = y_s, \quad \forall s \in S$$
$$w_{s,c} \leq x_c, \quad \forall s \in S, \forall c \in C$$

### R5: Un acopio solo puede asignarse a una central si está abierto
$$\text{(implícito en R4)}$$

### R6: Flujo de conservación (lo que entra al acopio sale hacia la central)
$$\sum_{m \in M} \sum_{p \in P} o_{p,m} \cdot z_{m,s} = \sum_{c \in C} \sum_{p \in P} o_{p,s} \cdot w_{s,c}, \quad \forall s \in S$$

### R7: Capacidad de acopio (opcional)
$$cap_{min} \cdot y_s \leq \sum_{m \in M} \sum_{p \in P} o_{p,m} \cdot z_{m,s} \leq cap_{max} \cdot y_s, \quad \forall s \in S$$

## 7. Columnas esperadas de archivos de entrada

| Archivo | Columnas requeridas | Usado por |
|---------|---------------------|-----------|
| `zonas.csv` | `cod_dane`, `municipio`, `zona`, `es_centro_zona` | Agrupamiento de municipios en zonas |
| `oferta_escenarios.csv` | `producto`, `cod_dane`, `año`, `oferta_bajo`, `oferta_base`, `oferta_alto` | Oferta por producto, municipio, año |
| `escenarios.csv` | `id_escenario`, `oferta`, `consumo`, `pct_nacional`, `pct_exportacion`, `zona`, `volumen_nacional`, `volumen_exportacion` | Escenarios de mezcla nacional/exportación |
| `matriz_tiempos.csv` | `origen`, `destino`, `minutos`, `distancia_km`, `metodo` | Tiempos de viaje municipio-municipio y municipio-destino |
| `municipios_coordenadas.csv` | `cod_dane`, `municipio`, `lat`, `lon` | Coordenadas para mapas y cálculo de distancias |
| `destinos_coordenadas.csv` | `id_destino`, `nombre`, `lat`, `lon` | Coordenadas de mercados y puertos |
| `produccion_promedio_municipio.csv` | `cod_dane`, `municipio`, `producto`, `prod_prom_t_2019_2023` | Producción promedio histórica por municipio |

## 8. Entregables de esta tarea

1. `docs/formulacion_optimizacion.md` (este documento)
2. Notebook o script del modelo funcionando con datos ficticios (~15-20 municipios)
3. Listado de columnas que espera de cada archivo de entrada (tabla R7 arriba)

## 9. Dependencias

- Carlos necesita este texto el 13 de nov para el diagrama de frontera ML ↔ optimización
- Acordar con Samuel y Ceyni los nombres de columnas de `zonas.csv`, `escenarios.csv` y `oferta_escenarios.csv`
- Si Ceyni no incluye los mercados nacionales en la matriz de tiempos, usar distancias aproximadas

---

## 10. Formulación implementada (integración con arendonc2)

Esta sección documenta lo que implementa `src/optimizacion/modelo_real.py` tras la
integración, que **precisa y corrige** la formulación original de arriba. El modelo
es lineal (resoluble por CBC; se usa SCIP por velocidad) y toma los datos del
adaptador `preparar_para_solver(id_escenario, anio)`.

### Parámetros efectivos
- $q_m$: excedente **conocido** del municipio $m$ (t). Los productos con consumo
  pendiente se excluyen (no aportan volumen). $Q = \sum_m q_m$ es el volumen total
  conocido y cota válida del flujo.
- $t_{a,b}$: tiempo de viaje (min), validado (presente, finito, no negativo; sin
  `.get(...,0)`).
- Pesos de destino: la cuota de cada grupo (nacional/exportación) se reparte entre
  sus destinos con pesos internos que suman 1 (por defecto, reparto igual).

### Variables
$x_c, y_s, z_{m,s}, w_{s,c} \in \{0,1\}$ (z, w relajadas a $[0,1]$; salen enteras por
la estructura de asignación) y **$f_{s,c} \ge 0$** (toneladas transportadas de $s$ a $c$).

### Restricción R6 corregida — conservación con flujo explícito
$$\sum_{c \in C} f_{s,c} = \sum_{m \in M} q_m \, z_{m,s}, \quad \forall s \in S$$
$$f_{s,c} \le Q \, w_{s,c}, \quad \forall s,c$$

Se **elimina** la igualdad incorrecta que usaba $o_{p,s}$ (oferta del propio
municipio satélite) como salida. El tramo satélite→central es **obligatorio**.

### Modos territoriales
- **Libre:** exactamente 5 satélites, asignación municipal sin restricción de zona.
- **Zonas:** un satélite por cada una de las 5 zonas; cada municipio se asigna a un
  satélite de su misma zona (los centros de `zonas.csv` son referencia, no se fuerzan).
  Pedir $k \ne$ nº de zonas lanza error antes de resolver.

### Objetivo (unidades: toneladas × minutos, t·min)
$$A = \underbrace{\sum_{m,s} q_m\, t_{m,s}\, z_{m,s}}_{A_1:\ \text{recolección}} +
      \underbrace{\sum_{s,c} f_{s,c}\, t_{s,c}}_{A_2:\ \text{satélite}\to\text{central}}$$
$$B = Q \sum_{c} x_c \sum_{d} \text{peso}_d\, t_{c,d} \quad (\text{central}\to\text{destinos})$$
$$\min\ \lambda A + (1-\lambda) B$$

Los mismos $A$ y $B$ se usan en resultados, en el gráfico de soluciones no dominadas
(barrido de $\lambda$, con filtro de dominancia y tolerancia relativa documentada) y
en la comparación libre/zonas.

### R7 — Capacidades: NO se implementan
La versión base **no** impone capacidad mínima ni máxima por acopio, por falta de
valores respaldados. Es un supuesto declarado aquí y en el tablero; no se inventan
capacidades.

### Integralidad, solver y calidad de la solución
- $x, y$ son binarias; $z, w$ se relajan a $[0,1]$ (la asignación es una p-mediana
  con relajación LP integral). **La integralidad se comprueba antes de aceptar cada
  solución. Si se detectan asignaciones fraccionarias fuera de la tolerancia
  (`tol_int = 1e-6`), la ejecución genera un error explícito.** También se verifica
  que cada municipio tenga un satélite abierto, que cada satélite abierto enlace con
  la única central, y que flujos y costos sean coherentes (no se redondea en silencio).
- Solver: SCIP (CBC de respaldo). Se reporta un **diagnóstico** por solución:
  solver, estado, objetivo, mejor cota, **brecha efectiva**
  $= |obj - \text{mejor\_cota}| / (|obj| + 10^{-9})$, tiempo, brecha solicitada y si
  el solver la aceptó. El `gap_relativo` por defecto es **0**. Solicitar gap 0 exige
  buscar una solución sin brecha, pero el límite de tiempo puede impedir alcanzarla;
  la calidad obtenida se informa mediante el estado del solver, la mejor cota y la
  brecha efectiva.
- Comparación libre vs zonas (2024, oferta base, consumo base, 80/20, λ=0.5, k=5),
  resuelta con brecha solicitada 0: en los resultados guardados ambos modos
  reportaron estado **OPTIMAL** y **brecha efectiva 0**; objetivo libre 167.211.081
  vs zonas 168.052.318 t·min, **diferencia 0,50 %** (no es artefacto de tolerancia).
  Detalle en `data/results/arendonc2/comparacion_configuraciones.csv`.

### Supuestos y limitaciones vigentes
- Mezclas nacional/exportación: escenarios de **sensibilidad**, sin respaldo empírico.
- Cobertura parcial de consumo: productos pendientes excluidos del volumen.
- Geometrías de zonas: GADM (pendiente de aceptación como sustituto del MGN del DANE).

---
*Autor original de las secciones 1–9: Samuel Gutiérrez Jaramillo (12-16 nov 2026).*
*Sección 10 (formulación implementada): integración con arendonc2.*