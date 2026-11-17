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
*Autor: Samuel Gutiérrez Jaramillo*  
*Fecha: 12-16 nov 2026*