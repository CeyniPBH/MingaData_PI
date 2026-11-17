"""
Modelo de optimización con DATOS REALES para la pantalla 3 del tablero.
Calcula:
- Central y acopios satélite óptimos usando OR-Tools
- Frontera de Pareto variando λ (recolección vs distribución)
- Tabla de estabilidad por escenario (bajo/base/alto)

Uso: python src/optimizacion/modelo_real.py
"""

import math
import numpy as np
import pandas as pd
from ortools.linear_solver import pywraplp
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_CLEAN = ROOT / "data" / "clean"
DATA_RES = ROOT / "data" / "results" / "ML_Ce"

# =============================================================================
# CARGA DE DATOS REALES
# =============================================================================

def cargar_datos_reales():
    """Carga municipios, oferta y matriz de tiempos desde archivos reales."""
    municipios = pd.read_csv(DATA_CLEAN / "municipios_coordenadas.csv", dtype={"cod_dane": str})
    destinos = pd.read_csv(DATA_CLEAN / "destinos_coordenadas.csv")
    matriz = pd.read_csv(DATA_CLEAN / "matriz_tiempos.csv", dtype={"origen": str, "destino": str})
    oferta = pd.read_csv(DATA_RES / "oferta_escenarios.csv", dtype={"cod_dane": str})
    return municipios, destinos, matriz, oferta


def construir_matriz_tiempos_dict(matriz, municipios, destinos):
    """Construye dict {(origen, destino): minutos} desde la matriz real."""
    tiempos = {}
    for _, row in matriz.iterrows():
        tiempos[(row["origen"], row["destino"])] = row["minutos"]
    return tiempos


def obtener_oferta_por_municipio(oferta, ano=2024, escenario="base"):
    """Devuelve dict {cod_dane: oferta_total_ton} para un año y escenario dados."""
    col_ano = [c for c in oferta.columns if "ano" in c.lower() or "año" in c.lower()][0]
    sub = oferta[(oferta[col_ano] == ano)]
    col = "oferta_{}".format(escenario)
    agg = sub.groupby("cod_dane")[col].sum().to_dict()
    return agg


# =============================================================================
# MODELO OR-TOOLS CON DATOS REALES
# =============================================================================

def resolver_ubicacion(municipios, destinos, tiempos, oferta_mun, k=4, lam=0.5,
                       pct_nac=0.8, pct_exp=0.2):
    """
    Resuelve el problema de ubicación con datos reales usando OR-Tools.

    Retorna dict con central, satelites, asignaciones, costos.
    """
    solver = pywraplp.Solver.CreateSolver("CBC")
    if not solver:
        raise RuntimeError("No se pudo crear el solver CBC")

    cod_mun = [m for m in municipios["cod_dane"].tolist() if m in oferta_mun]
    # Incluir todos los municipios como candidatos aunque tengan oferta 0
    cod_mun_all = municipios["cod_dane"].tolist()
    oferta = {m: oferta_mun.get(m, 0.0) for m in cod_mun_all}

    C = cod_mun_all  # candidatos a central
    S = cod_mun_all  # candidatos a satelite

    # Variables
    x = {c: solver.BoolVar("x_{}".format(c)) for c in C}
    y = {s: solver.BoolVar("y_{}".format(s)) for s in S}
    z = {(m, s): solver.BoolVar("z_{}_{}".format(m, s)) for m in cod_mun_all for s in S}
    w = {(s, c): solver.BoolVar("w_{}_{}".format(s, c)) for s in S for c in C}

    # Restricciones
    # Una sola central
    solver.Add(solver.Sum([x[c] for c in C]) == 1)

    # Exactamente k satelites
    solver.Add(solver.Sum([y[s] for s in S]) == k)

    # Cada municipio asignado a un satelite abierto
    for m in cod_mun_all:
        solver.Add(solver.Sum([z[(m, s)] for s in S]) == 1)
        for s in S:
            solver.Add(z[(m, s)] <= y[s])

    # Cada satelite asignado a una central abierta
    for s in S:
        solver.Add(solver.Sum([w[(s, c)] for c in C]) == y[s])
        for c in C:
            solver.Add(w[(s, c)] <= x[c])

    # Funcion objetivo
    # Z1: recoleccion (municipio -> satelite)
    costo_recoleccion = solver.Sum([
        oferta[m] * tiempos.get((m, s), 0) * z[(m, s)]
        for m in cod_mun_all for s in S
    ])

    # Z2: distribucion (central -> destinos ponderado)
    # costo_unitario_dist[c] = sum_d tiempo[c][d] * mezcla[d]
    volumen_total = sum(oferta.values())
    costo_unitario_dist = {}
    for c in C:
        costo_unitario_dist[c] = sum(
            tiempos.get((c, d), 0) * (pct_nac if d in ("DEST_CALI", "DEST_BOGOTA", "DEST_MEDELLIN") else pct_exp)
            for d in [r["id_destino"] for _, r in destinos.iterrows()]
        )

    costo_distribucion = solver.Sum([
        x[c] * costo_unitario_dist[c] * volumen_total
        for c in C
    ])

    solver.Minimize(lam * costo_recoleccion + (1 - lam) * costo_distribucion)

    # Resolver
    status = solver.Solve()

    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        return {"status": "INFACTIBLE"}

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
    for m in cod_mun_all:
        for s in S:
            if z[(m, s)].solution_value() > 0.5:
                asignaciones_m_s.append((m, s))

    asignaciones_s_c = []
    for s in S:
        for c in C:
            if w[(s, c)].solution_value() > 0.5:
                asignaciones_s_c.append((s, c))

    # Calcular costos finales
    z1_final = sum(oferta[m] * tiempos.get((m, s), 0) for (m, s) in asignaciones_m_s)
    costo_unit = {}
    for c in C:
        costo_unit[c] = sum(
            tiempos.get((c, d), 0) * (pct_nac if d in ("DEST_CALI", "DEST_BOGOTA", "DEST_MEDELLIN") else pct_exp)
            for d in [r["id_destino"] for _, r in destinos.iterrows()]
        )
    z2_final = costo_unit[central] * volumen_total

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
# FRONTERA DE PARETO REAL
# =============================================================================

def calcular_frontera_pareto(municipios, destinos, tiempos, oferta_mun,
                             k=4, lambdas=None, pct_nac=0.8, pct_exp=0.2):
    """Calcula la frontera de Pareto variando lambda."""
    if lambdas is None:
        lambdas = [i / 10 for i in range(11)]

    datos = []
    for lam in lambdas:
        res = resolver_ubicacion(
            municipios, destinos, tiempos, oferta_mun,
            k=k, lam=lam, pct_nac=pct_nac, pct_exp=pct_exp
        )
        if res["status"] in ("OPTIMAL", "FEASIBLE"):
            # Obtener nombre de la central
            cen_row = municipios[municipios["cod_dane"] == res["central"]]
            cen_nombre = cen_row["municipio"].iloc[0] if not cen_row.empty else res["central"]
            datos.append({
                "lambda": lam,
                "central": "{} ({})".format(cen_nombre, res["central"]),
                "z1": res["costo_recoleccion"],
                "z2": res["costo_distribucion"],
                "costo_total": res["costo_total"],
            })
    return pd.DataFrame(datos)


# =============================================================================
# TABLA DE ESTABILIDAD REAL
# =============================================================================

def calcular_estabilidad(municipios, destinos, tiempos, oferta,
                         k=4, lam=0.5, anos=[2024], escenarios=["bajo", "base", "alto"]):
    """Calcula qué municipio es central en cada escenario."""
    datos = []
    for ano in anos:
        for esc in escenarios:
            oferta_mun = obtener_oferta_por_municipio(oferta, ano=ano, escenario=esc)
            res = resolver_ubicacion(
                municipios, destinos, tiempos, oferta_mun,
                k=k, lam=lam, pct_nac=0.8, pct_exp=0.2
            )
            if res["status"] in ("OPTIMAL", "FEASIBLE"):
                cen_row = municipios[municipios["cod_dane"] == res["central"]]
                cen_nombre = cen_row["municipio"].iloc[0] if not cen_row.empty else res["central"]
                datos.append({
                    "ano": ano,
                    "escenario": esc,
                    "central": "{} ({})".format(cen_nombre, res["central"]),
                    "costo_total": res["costo_total"],
                })
    return pd.DataFrame(datos)


# =============================================================================
# EJECUCION PRINCIPAL
# =============================================================================

def main():
    print("=" * 70)
    print("MODELO DE OPTIMIZACION CON DATOS REALES")
    print("=" * 70)
    print()

    municipios, destinos, matriz, oferta = cargar_datos_reales()
    tiempos = construir_matriz_tiempos_dict(matriz, municipios, destinos)

    print("Municipios: {}".format(len(municipios)))
    print("Destinos: {}".format(len(destinos)))
    print("Entradas matriz tiempos: {}".format(len(matriz)))

    # Oferta para 2024, escenario base
    oferta_mun = obtener_oferta_por_municipio(oferta, ano=2024, escenario="base")
    print("Municipios con oferta 2024-base: {}".format(len(oferta_mun)))
    print()

    # Resolver para 2024, base, k=4, lambda=0.5
    print("--- Resolviendo ubicacion (2024, base, k=4, lambda=0.5) ---")
    res = resolver_ubicacion(municipios, destinos, tiempos, oferta_mun, k=4, lam=0.5)
    print("Estado: {}".format(res["status"]))
    print("Central: {}".format(res["central"]))
    cen_row = municipios[municipios["cod_dane"] == res["central"]]
    print("Nombre central: {}".format(cen_row["municipio"].iloc[0] if not cen_row.empty else "N/A"))
    print("Satelites: {}".format(res["satelites"]))
    print("Costo recoleccion: {:,.0f}".format(res["costo_recoleccion"]))
    print("Costo distribucion: {:,.0f}".format(res["costo_distribucion"]))
    print("Costo total: {:,.0f}".format(res["costo_total"]))
    print()

    # Frontera de Pareto
    print("--- Calculando frontera de Pareto ---")
    df_pareto = calcular_frontera_pareto(municipios, destinos, tiempos, oferta_mun, k=4)
    print(df_pareto.to_string(index=False))
    print()

    # Estabilidad
    print("--- Calculando estabilidad por escenario ---")
    df_estab = calcular_estabilidad(municipios, destinos, tiempos, oferta,
                                    k=4, lam=0.5, anos=[2024],
                                    escenarios=["bajo", "base", "alto"])
    print(df_estab.to_string(index=False))

    print()
    print("=" * 70)
    print("MODELO REAL COMPLETADO")
    print("=" * 70)


if __name__ == "__main__":
    main()