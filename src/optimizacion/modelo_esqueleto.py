"""
Modelo de localización de instalaciones en dos niveles con OR-Tools.
Esqueleto funcionando con datos ficticios (~15 municipios).

Problema: Ubicar una central de acopio y k acopios satélite para minimizar
el costo de recolección (municipio -> acopio) y distribución (central -> destinos).

Uso: python src/optimizacion/modelo_esqueleto.py
"""

import math
import numpy as np
import pandas as pd
from ortools.linear_solver import pywraplp


# =============================================================================
# 1. DATOS FICTICIOS (15 municipios del Valle del Cauca)
# =============================================================================

MUNICIPIOS_FICTICIOS = [
    # cod_dane, municipio, lat, lon, oferta_total_ton
    ("76001", "Cali", 3.4137, -76.5213, 15000),
    ("76109", "Buenaventura", 3.8757, -77.0107, 8000),
    ("76111", "Buga", 3.9007, -76.2990, 12000),
    ("76147", "Cartago", 4.7422, -75.9244, 9000),
    ("76520", "Palmira", 3.5315, -76.2988, 11000),
    ("76736", "Sevilla", 4.2707, -75.9316, 7000),
    ("76834", "Tulua", 4.0854, -76.1977, 10000),
    ("76892", "Yumbo", 3.5401, -76.4999, 6000),
    ("76246", "El Cairo", 4.7609, -76.2216, 5000),
    ("76364", "Jamundi", 3.2588, -76.5385, 8500),
    ("76622", "Roldanillo", 4.4136, -76.1523, 6500),
    ("76400", "La Union", 4.5339, -76.0997, 4000),
    ("76606", "Restrepo", 3.8214, -76.5233, 5500),
    ("76250", "El Dovio", 4.5105, -76.2371, 3000),
    ("76869", "Vijes", 3.6987, -76.4419, 4500),
]

# Destinos: Buenaventura, Aeropuerto Palmira, Cali, Bogota, Medellin
DESTINOS_FICTICIOS = [
    ("DEST_BUENAVENTURA", "Puerto de Buenaventura", 3.8757, -77.0107),
    ("DEST_AEROPUERTO_PALMIRA", "Aeropuerto Alfonso Bonilla Aragon (Palmira)", 3.5432, -76.3816),
    ("DEST_CALI", "Mercado Cali", 3.4137, -76.5213),
    ("DEST_BOGOTA", "Mercado Bogota", 4.6493, -74.1070),
    ("DEST_MEDELLIN", "Mercado Medellin", 6.2466, -75.5818),
]

# Parametros del modelo
K_SATELITES = 4          # numero de acopios satelite a abrir
LAMBDA = 0.5             # peso entre recoleccion (lambda) y distribucion (1-lambda)
PCT_NACIONAL = 0.8       # proporcion que va a mercado nacional
PCT_EXPORTACION = 0.2    # proporcion que va a exportacion


def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia en linea recta entre dos puntos (km)."""
    R = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def tiempo_viaje_min(dist_km, velocidad_kmh=45.0, factor_ruta=1.4):
    """Tiempo de viaje en minutos (distancia recta * factor / velocidad)."""
    return (dist_km * factor_ruta / velocidad_kmh) * 60.0


def generar_matriz_tiempos(municipios, destinos):
    """Genera matriz de tiempos municipio-municipio y municipio-destino."""
    tiempos = {}
    nodos = {m[0]: (m[2], m[3]) for m in municipios}
    todos_nodos = dict(nodos)
    for d in destinos:
        todos_nodos[d[0]] = (d[2], d[3])

    origenes = [m[0] for m in municipios]
    destinos_ids = [d[0] for d in destinos]

    for o in origenes:
        for d in origenes + destinos_ids:
            if o == d:
                tiempos[(o, d)] = 0.0
            else:
                km = haversine_km(*nodos[o], *todos_nodos[d])
                tiempos[(o, d)] = tiempo_viaje_min(km)
    return tiempos, todos_nodos


# =============================================================================
# 2. MODELO OR-TOOLS
# =============================================================================

def resolver_modelo(municipios, destinos, tiempos, k=K_SATELITES, lam=LAMBDA,
                    pct_nac=PCT_NACIONAL, pct_exp=PCT_EXPORTACION):
    """
    Resuelve el problema de localizacion de instalaciones en dos niveles.

    Retorna un dict con la solución: central, satelites, asignaciones, costos.
    """
    solver = pywraplp.Solver.CreateSolver("CBC")
    if not solver:
        raise RuntimeError("No se pudo crear el solver CBC de OR-Tools")

    cod_mun = [m[0] for m in municipios]
    oferta = {m[0]: m[4] for m in municipios}
    id_dest = [d[0] for d in destinos]

    # Conjuntos candidatos
    C = cod_mun  # candidatos a central (todos los municipios)
    S = cod_mun  # candidatos a satelite (todos los municipios)

    # =========================================================================
    # VARIABLES
    # =========================================================================
    x = {c: solver.BoolVar(f"x_{c}") for c in C}           # abrir central en c
    y = {s: solver.BoolVar(f"y_{s}") for s in S}           # abrir satelite en s
    z = {(m, s): solver.BoolVar(f"z_{m}_{s}") for m in cod_mun for s in S}  # m asignado a s
    w = {(s, c): solver.BoolVar(f"w_{s}_{c}") for s in S for c in C}         # s asignado a c

    # =========================================================================
    # RESTRICCIONES
    # =========================================================================

    # R1: Una sola central
    solver.Add(solver.Sum([x[c] for c in C]) == 1)

    # R2: Exactly k satelites
    solver.Add(solver.Sum([y[s] for s in S]) == k)

    # R3: Cada municipio asignado a un satelite abierto
    for m in cod_mun:
        solver.Add(solver.Sum([z[(m, s)] for s in S]) == 1)
        for s in S:
            solver.Add(z[(m, s)] <= y[s])

    # R4: Cada satelite asignado a una central abierta
    for s in S:
        solver.Add(solver.Sum([w[(s, c)] for c in C]) == y[s])
        for c in C:
            solver.Add(w[(s, c)] <= x[c])

    # =========================================================================
    # FUNCION OBJETIVO
    # =========================================================================

    # Z1: Costo de recoleccion (municipio -> satelite)
    # oferta[m] * tiempo[m][s] * z[m,s]  (oferta es constante, z es binaria -> lineal)
    costo_recoleccion = solver.Sum([
        oferta[m] * tiempos[(m, s)] * z[(m, s)]
        for m in cod_mun for s in S
    ])

    # Z2: Costo de distribucion (central -> destinos)
    # Formulacion lineal: para cada central c, costo_unitario_dist[c] =
    #   sum_d tiempo[c][d] * mezcla[d]
    # Z2 = sum_c x[c] * costo_unitario_dist[c] * VOLUMEN_TOTAL
    # DONDE VOLUMEN_TOTAL es una constante (suma de todas las ofertas).
    # Esto es lineal porque x[c] es binaria y el resto son constantes.
    volumen_total = sum(oferta.values())  # constante, no variable de OR-Tools
    costo_unitario_dist = {}
    for c in C:
        costo_unitario_dist[c] = sum(
            tiempos[(c, d)] * (pct_nac if d in ("DEST_CALI", "DEST_BOGOTA", "DEST_MEDELLIN") else pct_exp)
            for d in id_dest
        )

    costo_distribucion = solver.Sum([
        x[c] * costo_unitario_dist[c] * volumen_total
        for c in C
    ])

    # Objetivo combinado
    solver.Minimize(lam * costo_recoleccion + (1 - lam) * costo_distribucion)

    # =========================================================================
    # RESOLVER
    # =========================================================================
    status = solver.Solve()

    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        return {"status": "INFACTIBLE", "mensaje": "No se encontro solucion factible"}

    # Extraer solucion
    central = None
    for c in C:
        if x[c].solution_value() > 0.5:
            central = c
            break

    satelites = []
    for s in S:
        if y[s].solution_value() > 0.5:
            satelites.append(s)

    asignaciones_m_s = []
    for m in cod_mun:
        for s in S:
            if z[(m, s)].solution_value() > 0.5:
                asignaciones_m_s.append((m, s))

    asignaciones_s_c = []
    for s in S:
        for c in C:
            if w[(s, c)].solution_value() > 0.5:
                asignaciones_s_c.append((s, c))

    # Calcular costos finales
    z1_final = sum(oferta[m] * tiempos[(m, s)] for (m, s) in asignaciones_m_s)
    # Z2 consistente con la formulación lineal del modelo
    costo_unitario_dist = {}
    for c in C:
        costo_unitario_dist[c] = sum(
            tiempos[(c, d)] * (pct_nac if d in ("DEST_CALI", "DEST_BOGOTA", "DEST_MEDELLIN") else pct_exp)
            for d in id_dest
        )
    z2_final = costo_unitario_dist[central] * sum(oferta.values())

    return {
        "status": "OPTIMAL" if status == pywraplp.Solver.OPTIMAL else "FEASIBLE",
        "central": central,
        "satelites": satelites,
        "asignaciones_municipio_satelite": asignaciones_m_s,
        "asignaciones_satelite_central": asignaciones_s_c,
        "costo_recoleccion": z1_final,
        "costo_distribucion": z2_final,
        "costo_total": lam * z1_final + (1 - lam) * z2_final,
        "k": k,
        "lambda": lam,
    }


# =============================================================================
# 3. EJECUCION PRINCIPAL
# =============================================================================

def main():
    print("=" * 70)
    print("MODELO DE UBICACION DE CENTRAL Y ACOPIOS SATELITE (OR-Tools)")
    print("=" * 70)
    print()

    # Generar matriz de tiempos
    tiempos, todos_nodos = generar_matriz_tiempos(MUNICIPIOS_FICTICIOS, DESTINOS_FICTICIOS)

    print(f"Municipios: {len(MUNICIPIOS_FICTICIOS)}")
    print(f"Destinos: {len(DESTINOS_FICTICIOS)}")
    print(f"Acopios satelite a abrir (k): {K_SATELITES}")
    print(f"Peso recoleccion (lambda): {LAMBDA}")
    print(f"Mezcla nacional/exportacion: {PCT_NACIONAL:.0%} / {PCT_EXPORTACION:.0%}")
    print()

    # Resolver
    resultado = resolver_modelo(
        MUNICIPIOS_FICTICIOS, DESTINOS_FICTICIOS, tiempos,
        k=K_SATELITES, lam=LAMBDA,
        pct_nac=PCT_NACIONAL, pct_exp=PCT_EXPORTACION
    )

    print("-" * 70)
    print("RESULTADOS")
    print("-" * 70)
    print(f"Estado: {resultado['status']}")
    print(f"Central seleccionada: {resultado['central']}")
    m_central = next(m for m in MUNICIPIOS_FICTICIOS if m[0] == resultado['central'])
    print(f"  Nombre: {m_central[1]}")
    print(f"  Coordenadas: ({m_central[2]:.4f}, {m_central[3]:.4f})")
    print(f"Acopios satelite ({len(resultado['satelites'])}):")
    for s in resultado['satelites']:
        m = next(m for m in MUNICIPIOS_FICTICIOS if m[0] == s)
        print(f"  - {m[1]} ({s})")
    print()
    print("Asignaciones Municipio -> Satelite:")
    for m_id, s_id in resultado['asignaciones_municipio_satelite']:
        m = next(m for m in MUNICIPIOS_FICTICIOS if m[0] == m_id)
        s = next(m for m in MUNICIPIOS_FICTICIOS if m[0] == s_id)
        print(f"  {m[1]} -> {s[1]}")
    print()
    print("Asignaciones Satelite -> Central:")
    for s_id, c_id in resultado['asignaciones_satelite_central']:
        s = next(m for m in MUNICIPIOS_FICTICIOS if m[0] == s_id)
        c = next(m for m in MUNICIPIOS_FICTICIOS if m[0] == c_id)
        print(f"  {s[1]} -> {c[1]} (central)")
    print()
    print("-" * 70)
    print("COSTOS")
    print("-" * 70)
    print(f"Costo de recoleccion: {resultado['costo_recoleccion']:,.0f} (ton*min)")
    print(f"Costo de distribucion: {resultado['costo_distribucion']:,.0f} (ton*min)")
    print(f"Costo total ponderado: {resultado['costo_total']:,.0f} (ton*min)")
    print()
    print("=" * 70)
    print("MODELO EJECUTADO CORRECTAMENTE")
    print("=" * 70)


if __name__ == "__main__":
    main()