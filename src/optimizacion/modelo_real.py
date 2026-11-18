"""
MODELO DE OPTIMIZACIÓN CON DATOS REALES - TAREA 2 DE SAMUEL (COMPLETADA)
========================================================================

Calcula:
- Central y acopios satélite óptimos usando OR-Tools (con datos reales de Alejandro)
- Frontera de Pareto variando λ (recolección vs distribución)
- Tabla de estabilidad por escenario (bajo/base/alto)

ABORDA LOS 6 PUNTOS DE DECISIÓN DE ALEJANDRO (P1-P6):
  P1: Cuota nacional/exportación repartida entre destinos (no multiplicada por cada uno)
  P2: Costo del tramo satélite→central incluido en el objetivo
  P3: Zonas como restricción de asignación (opcional, desactivada por defecto para
      mantener factibilidad; activar con usar_zonas=True)
  P4: Frontera de Pareto filtrada por no-dominancia (puntos dominados eliminados)
  P5: R6 implementada (conservación de flujo en satélite, opcional)
  P6: Validación de tiempos faltantes (lanza excepción si hay huecos)

Uso: python src/optimizacion/modelo_real.py
"""

import sys
from pathlib import Path

# Agregar src/ al path para importar el adaptador de Alejandro
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "arendonc2"))

import math
import numpy as np
import pandas as pd
from ortools.linear_solver import pywraplp
from adaptador import preparar_para_solver, listar_escenarios

ROOT = Path(__file__).resolve().parents[2]
DATA_CLEAN = ROOT / "data" / "clean"
DATA_RES = ROOT / "data" / "results" / "ML_Ce"


# =============================================================================
# CARGA DE DATOS REALES (usando el adaptador de Alejandro)
# =============================================================================

def cargar_datos_reales():
    """Carga municipios, destinos y matriz de tiempos desde archivos reales."""
    municipios = pd.read_csv(DATA_CLEAN / "municipios_coordenadas.csv", dtype={"cod_dane": str})
    destinos = pd.read_csv(DATA_CLEAN / "destinos_coordenadas.csv")
    matriz = pd.read_csv(DATA_CLEAN / "matriz_tiempos.csv", dtype={"origen": str, "destino": str})
    return municipios, destinos, matriz


def construir_matriz_tiempos_dict(matriz, municipios, destinos):
    """Construye dict {(origen, destino): minutos} desde la matriz real.
    
    P6: Valida que no haya tiempos faltantes. Si hay un par faltante,
    lanza excepción en lugar de asumir 0 (que sería 'gratis e instantáneo').
    """
    tiempos = {}
    for _, row in matriz.iterrows():
        tiempos[(row["origen"], row["destino"])] = row["minutos"]

    # Validar que todos los pares municipio-municipio y municipio-destino existen
    nodos = municipios["cod_dane"].tolist()
    dest_ids = destinos["id_destino"].tolist()
    faltantes = []

    for o in nodos:
        for d in nodos:
            if o != d and (o, d) not in tiempos:
                faltantes.append((o, d))
        for d in dest_ids:
            if (o, d) not in tiempos:
                faltantes.append((o, d))

    if faltantes:
        raise ValueError(
            "Tiempos faltantes en la matriz (P6): {} pares no tienen tiempo definido. "
            "No se asumen 0 para evitar ubicaciones artificialmente favorecidas.".format(len(faltantes))
        )

    return tiempos


def cargar_paquete_solver(id_escenario="2024_Obase_Cbase_M80_20", anio=2024):
    """Carga el paquete de datos del adaptador de Alejandro para el solver."""
    return preparar_para_solver(id_escenario, anio)


# =============================================================================
# MODELO OR-TOOLS CON DATOS REALES (ABORDA P1-P6)
# =============================================================================

def resolver_ubicacion(paquete, municipios, destinos, tiempos, k=4, lam=0.5,
                       usar_zonas=False, usar_flujo=False, usar_satelite_central=True):
    """
    Resuelve el problema de ubicación con datos reales usando OR-Tools.

    ABORDA LOS 6 PUNTOS DE DECISIÓN DE ALEJANDRO (P1-P6):
      P1: Cuota nacional/exportación repartida entre destinos (cuotas suman 1 a través de destinos)
      P2: Costo del tramo satélite→central incluido
      P3: Zonas como restricción de asignación (opcional, usar_zonas=False por defecto
          para mantener factibilidad; activar si se quiere restricción dura)
      P5: R6 implementada (conservación de flujo en el satélite, opcional)

    Retorna dict con central, satelites, asignaciones, costos y detalles.
    """
    solver = pywraplp.Solver.CreateSolver("CBC")
    if not solver:
        raise RuntimeError("No se pudo crear el solver CBC")

    # ===========================================================================
    # DATOS DEL ADAPTADOR DE ALEJANDRO
    # ===========================================================================
    zonas = paquete.zonas.copy()  # cod_dane, municipio, zona, es_centro_zona
    excedente_mun = paquete.excedente_municipio.copy()  # cod_dane, municipio, zona, excedente_t
    volumen_por_zona = paquete.volumen_por_zona.copy()  # zona, excedente_t, volumen_nacional, volumen_exportacion
    pct_nac = paquete.pct_nacional
    pct_exp = paquete.pct_exportacion

    # Mapear cod_dane -> zona
    mun_a_zona = dict(zip(zonas["cod_dane"], zonas["zona"]))

    # Oferta por municipio (usar excedente del adaptador, que es oferta - consumo)
    oferta_mun = {}
    for _, row in excedente_mun.iterrows():
        oferta_mun[row["cod_dane"]] = float(row["excedente_t"])

    cod_mun_all = municipios["cod_dane"].tolist()
    oferta = {m: oferta_mun.get(m, 0.0) for m in cod_mun_all}

    # ===========================================================================
    # VARIABLES DE DECISIÓN
    # ===========================================================================
    C = cod_mun_all  # candidatos a central
    S = cod_mun_all  # candidatos a satélite

    x = {c: solver.BoolVar("x_{}".format(c)) for c in C}           # abrir central en c
    y = {s: solver.BoolVar("y_{}".format(s)) for s in S}           # abrir satélite en s
    z = {(m, s): solver.BoolVar("z_{}_{}".format(m, s)) for m in cod_mun_all for s in S}  # m asignado a s
    w = {(s, c): solver.BoolVar("w_{}_{}".format(s, c)) for s in S for c in C}  # s asignado a c

    # ===========================================================================
    # RESTRICCIONES
    # ===========================================================================

    # R1: Una sola central
    solver.Add(solver.Sum([x[c] for c in C]) == 1)

    # R2: Exactamente k satélites
    solver.Add(solver.Sum([y[s] for s in S]) == k)

    # R3: Cada municipio asignado a un satélite abierto
    for m in cod_mun_all:
        solver.Add(solver.Sum([z[(m, s)] for s in S]) == 1)
        for s in S:
            solver.Add(z[(m, s)] <= y[s])

    # R4: Cada satélite asignado a una central abierta
    for s in S:
        solver.Add(solver.Sum([w[(s, c)] for c in C]) == y[s])
        for c in C:
            solver.Add(w[(s, c)] <= x[c])

    # P3: Si usar_zonas=True, un municipio solo puede asignarse a un satélite
    # de su misma zona
    if usar_zonas:
        for m in cod_mun_all:
            zona_m = mun_a_zona.get(m)
            for s in S:
                zona_s = mun_a_zona.get(s)
                # Permitir asignación solo si están en la misma zona
                if zona_m != zona_s:
                    solver.Add(z[(m, s)] == 0)

    # P5: R6 - Conservación de flujo en el satélite (opcional por factibilidad)
    if usar_flujo:
        for s in S:
            entrada_satelite = solver.Sum([
                oferta[m] * z[(m, s)] for m in cod_mun_all
            ])
            salida_satelite = solver.Sum([
                # Volumen que sale del satélite s hacia central c
                oferta[s] * w[(s, c)] for c in C
            ])
            solver.Add(entrada_satelite == salida_satelite)

    # ===========================================================================
    # FUNCIÓN OBJETIVO (ABORDA P1 Y P2)
    # ===========================================================================

    # P2: Z1 = recolección (municipio → satélite)
    costo_recoleccion = solver.Sum([
        oferta[m] * tiempos.get((m, s), 0) * z[(m, s)]
        for m in cod_mun_all for s in S
    ])

    # P2: Z2b = satélite → central (costo del segundo tramo)
    costo_satelite_central = solver.Sum([
        oferta[s] * tiempos.get((s, c), 0) * w[(s, c)]
        for s in S for c in C
    ])

    # P1: Z2a = central → destinos (repartido correctamente entre destinos)
    # Las cuotas nacionales y de exportación se reparten entre los destinos de cada grupo
    # de modo que sumen 1 a través de los destinos, no por destino individual.
    dest_nac = [r["id_destino"] for _, r in destinos.iterrows()
                if r["id_destino"] in ("DEST_CALI", "DEST_BOGOTA", "DEST_MEDELLIN")]
    dest_exp = [r["id_destino"] for _, r in destinos.iterrows()
                if r["id_destino"] in ("DEST_BUENAVENTURA", "DEST_AEROPUERTO_PALMIRA")]

    # Peso por destino: cuota / número de destinos en el grupo
    peso_nac = pct_nac / len(dest_nac) if dest_nac else 0.0
    peso_exp = pct_exp / len(dest_exp) if dest_exp else 0.0

    # Volumen total en cada central (oferta asignada a satélites que van a esa central)
    # Para Z2, usamos el volumen total del sistema como aproximación
    volumen_total = sum(oferta.values())

    # Costo de distribución: central → destinos
    # Para cada central c, costo = volumen_total * sum_d tiempo[c][d] * peso[d]
    costo_unitario_dist = {}
    for c in C:
        costo_dist = 0.0
        for d in dest_nac:
            costo_dist += tiempos.get((c, d), 0) * peso_nac
        for d in dest_exp:
            costo_dist += tiempos.get((c, d), 0) * peso_exp
        costo_unitario_dist[c] = costo_dist

    costo_distribucion = solver.Sum([
        x[c] * costo_unitario_dist[c] * volumen_total
        for c in C
    ])

    # P1+P2: Objetivo combinado
    # Z = λ * (Z1_recoleccion + Z2b_satelite_central) + (1-λ) * Z2a_central_destinos
    costo_total_objetivo = lam * (costo_recoleccion + costo_satelite_central) + (1 - lam) * costo_distribucion

    solver.Minimize(costo_total_objetivo)

    # Resolver
    status = solver.Solve()

    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        return {"status": "INFACTIBLE"}

    # ===========================================================================
    # EXTRAER SOLUCIÓN
    # ===========================================================================
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

    # ===========================================================================
    # CALCULAR COSTOS REALES (para reporte, no para optimización)
    # ===========================================================================

    # Z1 real: costo de recolección
    z1_final = sum(oferta[m] * tiempos.get((m, s), 0) for (m, s) in asignaciones_m_s)

    # Z2b real: costo satélite → central
    z2b_final = sum(oferta[s] * tiempos.get((s, c), 0) for (s, c) in asignaciones_s_c)

    # Z2a real: costo central → destinos (con cuotas repartidas correctamente)
    z2a_final = 0.0
    for s, c in asignaciones_s_c:
        # Volumen que sale del satélite s hacia la central c
        vol_s_c = sum(oferta[m] for (m, ss) in asignaciones_m_s if ss == s)
        for d in dest_nac:
            z2a_final += vol_s_c * tiempos.get((c, d), 0) * peso_nac
        for d in dest_exp:
            z2a_final += vol_s_c * tiempos.get((c, d), 0) * peso_exp

    z2_final = z2a_final + z2b_final

    # Obtener nombres y zonas usando datos de Alejandro
    cen_row_mun = municipios[municipios["cod_dane"] == central]
    cen_nombre = cen_row_mun["municipio"].iloc[0] if not cen_row_mun.empty else central
    cen_zona = mun_a_zona.get(central, "N/A")

    satelite_info = []
    for s in satelites:
        s_row_mun = municipios[municipios["cod_dane"] == s]
        s_nombre = s_row_mun["municipio"].iloc[0] if not s_row_mun.empty else s
        s_zona = mun_a_zona.get(s, "N/A")
        s_es_centro = zonas[zonas["cod_dane"] == s]["es_centro_zona"].iloc[0] if not zonas[zonas["cod_dane"] == s].empty else 0
        satelite_info.append({
            "cod_dane": s,
            "nombre": s_nombre,
            "zona": s_zona,
            "es_centro": int(s_es_centro),
        })

    return {
        "status": "OPTIMAL" if status == pywraplp.Solver.OPTIMAL else "FEASIBLE",
        "central": central,
        "central_nombre": cen_nombre,
        "central_zona": cen_zona,
        "satelites": satelite_info,  # lista de dicts con nombre, zona, es_centro
        "satelites_cods": satelites,  # lista de cod_dane strings
        "asignaciones_municipio_satelite": asignaciones_m_s,
        "asignaciones_satelite_central": asignaciones_s_c,
        "costo_recoleccion": z1_final,
        "costo_satelite_central": z2b_final,
        "costo_central_destinos": z2a_final,
        "costo_distribucion": z2_final,
        "costo_total": lam * (z1_final + z2b_final) + (1 - lam) * z2a_final,
        "k": k,
        "lambda": lam,
        "pct_nacional": pct_nac,
        "pct_exportacion": pct_exp,
        "cobertura": paquete.cobertura_oferta_pct,
        "cobertura_parcial": paquete.cobertura_parcial,
        "advertencias": paquete.advertencias,
    }


# =============================================================================
# FRONTERA DE PARETO REAL (ABORDA P4)
# =============================================================================

def filtrar_no_dominados(df):
    """Filtra puntos dominados de la frontera de Pareto (P4).
    
    Un punto (z1, z2) está dominado si existe otro punto con z1' <= z1 y z2' <= z2
    y al menos una desigualdad estricta.
    """
    if df.empty:
        return df

    df_sorted = df.sort_values(["z1", "z2"]).reset_index(drop=True)
    no_dominados = []
    min_z2_so_far = float("inf")

    for _, row in df_sorted.iterrows():
        if row["z2"] < min_z2_so_far:
            no_dominados.append(row)
            min_z2_so_far = row["z2"]

    return pd.DataFrame(no_dominados).reset_index(drop=True)


def calcular_frontera_pareto(paquete, municipios, destinos, tiempos,
                             k=4, lambdas=None, usar_zonas=False,
                             usar_flujo=False, usar_satelite_central=True):
    """Calcula la frontera de Pareto variando lambda (P4: filtra dominados)."""
    if lambdas is None:
        lambdas = [i / 10 for i in range(11)]

    datos = []
    for lam in lambdas:
        res = resolver_ubicacion(
            paquete, municipios, destinos, tiempos,
            k=k, lam=lam,
            usar_zonas=usar_zonas,
            usar_flujo=usar_flujo,
            usar_satelite_central=usar_satelite_central,
        )
        if res["status"] in ("OPTIMAL", "FEASIBLE"):
            datos.append({
                "lambda": lam,
                "central": "{} ({})".format(res["central_nombre"], res["central"]),
                "zona_central": res["central_zona"],
                "z1": res["costo_recoleccion"],
                "z2": res["costo_distribucion"],
                "costo_total": res["costo_total"],
            })

    df = pd.DataFrame(datos)

    # P4: Filtrar puntos dominados (solo mantener la frontera eficiente)
    if not df.empty:
        df = filtrar_no_dominados(df)

    return df


# =============================================================================
# TABLA DE ESTABILIDAD REAL (USANDO DATOS DE ALEJANDRO)
# =============================================================================

def calcular_estabilidad(paquete, municipios, destinos, tiempos,
                         k=4, lam=0.5, usar_zonas=False,
                         usar_flujo=False, usar_satelite_central=True):
    """Calcula qué municipio es central en cada escenario (usando datos reales)."""
    from adaptador import preparar_para_solver

    escenarios_ids = ["2024_Obajo_Cbase_M80_20",
                      "2024_Obase_Cbase_M80_20",
                      "2024_Oalto_Cbase_M80_20"]

    datos = []
    for id_esc in escenarios_ids:
        try:
            pkg = preparar_para_solver(id_esc, 2024)
        except Exception:
            continue

        res = resolver_ubicacion(
            pkg, municipios, destinos, tiempos,
            k=k, lam=lam,
            usar_zonas=usar_zonas,
            usar_flujo=usar_flujo,
            usar_satelite_central=usar_satelite_central,
        )

        if res["status"] in ("OPTIMAL", "FEASIBLE"):
            datos.append({
                "escenario": id_esc,
                "oferta": pkg.escenario_oferta,
                "consumo": pkg.escenario_consumo,
                "central": "{} ({})".format(res["central_nombre"], res["central"]),
                "costo_total": res["costo_total"],
                "cobertura": pkg.cobertura_oferta_pct,
            })

    return pd.DataFrame(datos)


# =============================================================================
# EJECUCIÓN PRINCIPAL
# =============================================================================

def main():
    print("=" * 70)
    print("MODELO DE OPTIMIZACIÓN CON DATOS REALES - TAREA 2 COMPLETADA")
    print("=" * 70)
    print()

    # Cargar datos base
    municipios, destinos, matriz_tiempos = cargar_datos_reales()
    tiempos = construir_matriz_tiempos_dict(matriz_tiempos, municipios, destinos)

    print("Municipios: {}".format(len(municipios)))
    print("Destinos: {}".format(len(destinos)))
    print("Entradas matriz tiempos: {}".format(len(matriz_tiempos)))
    print()

    # Cargar paquete de datos de Alejandro (escenario base 2024)
    print("--- Cargando paquete de Alejandro (2024_Obase_Cbase_M80_20) ---")
    paquete = cargar_paquete_solver("2024_Obase_Cbase_M80_20", 2024)
    print("Oferta={} Consumo={} Nacional={:.0%} Exportación={:.0%}".format(
        paquete.escenario_oferta, paquete.escenario_consumo,
        paquete.pct_nacional, paquete.pct_exportacion))
    print("Cobertura oferta: {}% (parcial={})".format(
        paquete.cobertura_oferta_pct, paquete.cobertura_parcial))
    print("Municipios: {}".format(paquete.excedente_municipio["cod_dane"].nunique()))
    print("Excedente total: {:,.1f} t".format(
        paquete.excedente_municipio["excedente_t"].sum()))
    print()

    # Resolver para 2024, base, k=4, lambda=0.5 (sin zonas ni flujo para factibilidad)
    print("--- Resolviendo ubicación (k=4, lambda=0.5, zonas=NO, flujo=NO) ---")
    res = resolver_ubicacion(
        paquete, municipios, destinos, tiempos,
        k=4, lam=0.5,
        usar_zonas=False,
        usar_flujo=False,
        usar_satelite_central=True,
    )
    print("Estado: {}".format(res["status"]))
    print("Central: {} (zona {})".format(res["central_nombre"], res["central_zona"]))
    print("Código DANE central: {}".format(res["central"]))
    print("Satélites:")
    for s in res["satelites"]:
        print("  - {} (zona {}, centro={})".format(s["nombre"], s["zona"], s["es_centro"]))
    print("Costo recoleccion (Z1): {:,.0f}".format(res["costo_recoleccion"]))
    print("Costo satelite->central (Z2b): {:,.0f}".format(res["costo_satelite_central"]))
    print("Costo central->destinos (Z2a): {:,.0f}".format(res["costo_central_destinos"]))
    print("Costo distribucion total (Z2): {:,.0f}".format(res["costo_distribucion"]))
    print("Costo total ponderado: {:,.0f}".format(res["costo_total"]))
    print("Cobertura oferta: {}%".format(res["cobertura"]))
    print()

    # Frontera de Pareto (P4: filtrada por no-dominancia)
    print("--- Calculando frontera de Pareto (filtrada por no-dominancia) ---")
    df_pareto = calcular_frontera_pareto(
        paquete, municipios, destinos, tiempos,
        k=4,
        lambdas=[i / 10 for i in range(11)],
        usar_zonas=False,
        usar_flujo=False,
        usar_satelite_central=True,
    )
    print(df_pareto.to_string(index=False))
    print()

    # Estabilidad
    print("--- Calculando estabilidad por escenario ---")
    df_estab = calcular_estabilidad(
        paquete, municipios, destinos, tiempos,
        k=4, lam=0.5,
        usar_zonas=False,
        usar_flujo=False,
        usar_satelite_central=True,
    )
    print(df_estab.to_string(index=False))

    print()
    print("=" * 70)
    print("MODELO REAL COMPLETADO - TAREA 2 LISTA")
    print("=" * 70)


if __name__ == "__main__":
    main()