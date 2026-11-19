"""
MODELO DE OPTIMIZACIÓN LOGÍSTICA CON DATOS REALES
=================================================

Ubica una central de acopio y sus acopios satélite minimizando el costo logístico
(toneladas × minutos, t·min). Usa los entregables corregidos de arendonc2 a través
del adaptador `preparar_para_solver(id_escenario, anio)`.

FORMULACIÓN (lineal, resoluble por CBC)

Conjuntos
  M  municipios (candidatos a central y a satélite)
  D  destinos (nacionales: Cali, Bogotá, Medellín; exportación: Buenaventura, aeropuerto)

Parámetros
  q_m          excedente CONOCIDO del municipio m (t). Pendientes excluidos por el adaptador.
  Q = sum_m q_m   excedente total conocido del escenario (cota válida del flujo)
  t[a,b]       tiempo de viaje a->b (min); validado, sin huecos
  pct_nac, pct_exp   cuotas nacional/exportación (suman 1)
  peso[d]      peso del destino d dentro de su grupo (los del grupo suman 1)

Variables
  x_c ∈ {0,1}         abrir central en c
  y_s ∈ {0,1}         abrir satélite en s
  z[m,s] ∈ {0,1}      municipio m asignado al satélite s
  w[s,c] ∈ {0,1}      enlace satélite s -> central c
  f[s,c] ≥ 0          toneladas transportadas de s a c (continua)

Restricciones
  R1  sum_c x_c = 1
  R2  sum_s y_s = k
  R3  sum_s z[m,s] = 1  ;  z[m,s] ≤ y_s
  R4  sum_c w[s,c] = y_s ; w[s,c] ≤ x_c
  R5  conservación de flujo por satélite:
        sum_c f[s,c] = sum_m q_m · z[m,s]      (todo lo recibido sale hacia la central)
  R6  vinculación del flujo:  f[s,c] ≤ Q · w[s,c]   (sólo fluye por enlaces abiertos)
  (zonas)  si modo="zonas": z[m,s]=0 si m y s están en zonas distintas, y un satélite por zona

Costos (t·min)
  A1 = sum_{m,s} q_m · t[m,s] · z[m,s]          recolección municipio->satélite
  A2 = sum_{s,c} f[s,c] · t[s,c]                 satélite->central (flujo explícito)
  A  = A1 + A2
  B  = Q · sum_d peso_grupo[d] · t[c*,d]         central->destinos (una central, todo el volumen Q)
  Objetivo = λ·A + (1-λ)·B

El tramo satélite->central es OBLIGATORIO (no hay opción para desactivarlo).
No se igualan volúmenes a oferta[s]; el flujo f es una variable continua explícita.

Uso: python src/optimizacion/modelo_real.py
"""

import sys
from pathlib import Path

# Agregar src/ al path para importar el adaptador de Alejandro
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "arendonc2"))

import numpy as np
import pandas as pd
from ortools.linear_solver import pywraplp
from adaptador import preparar_para_solver, listar_escenarios

ROOT = Path(__file__).resolve().parents[2]
DATA_CLEAN = ROOT / "data" / "clean"
DATA_RES = ROOT / "data" / "results" / "ML_Ce"

# Grupos de destinos por defecto (reparto igual dentro de cada grupo).
DESTINOS_NACIONALES = ("DEST_CALI", "DEST_BOGOTA", "DEST_MEDELLIN")
DESTINOS_EXPORTACION = ("DEST_BUENAVENTURA", "DEST_AEROPUERTO_PALMIRA")

# Tolerancia numérica para deduplicar/dominancia en el barrido de lambda (t·min relativos).
TOL_PARETO_REL = 1e-6

# Tolerancia de integralidad por defecto: un valor de variable binaria debe estar a
# <= TOL_INT de 0 o de 1. Si no, se considera fraccionario (no se redondea en silencio).
TOL_INT_DEFECTO = 1e-6


def _configurar_gap(solver, gap_relativo):
    """
    Configura la brecha relativa objetivo en SCIP o CBC con la sintaxis de cada uno.
    Devuelve (aceptado: bool, detalle: str). NO oculta fallos: informa si no se aplicó.
    """
    if not gap_relativo or gap_relativo <= 0:
        return True, "gap solicitado = 0 (óptimo certificado)"
    nombre = solver.SolverVersion().lower()
    intentos = []
    if "scip" in nombre:
        intentos = ["limits/gap = {}".format(gap_relativo)]
    elif "cbc" in nombre or "coin" in nombre:
        intentos = ["ratioGap {}".format(gap_relativo), "allowableGap {}".format(gap_relativo)]
    else:
        intentos = ["limits/gap = {}".format(gap_relativo)]
    for cadena in intentos:
        ok = solver.SetSolverSpecificParametersAsString(cadena)
        if ok:
            return True, "aplicado: '{}'".format(cadena)
    return False, "no aceptado por el solver ({}): intentos {}".format(nombre, intentos)

# Estados del solver (nombres legibles)
_ESTADOS = {
    pywraplp.Solver.OPTIMAL: "OPTIMAL",
    pywraplp.Solver.FEASIBLE: "FEASIBLE",
    pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
    pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
    pywraplp.Solver.ABNORMAL: "ABNORMAL",
    pywraplp.Solver.NOT_SOLVED: "NOT_SOLVED",
}


# =============================================================================
# CARGA DE DATOS Y MATRIZ DE TIEMPOS (validación estricta, P6)
# =============================================================================

def cargar_datos_reales():
    """Carga municipios, destinos y matriz de tiempos desde archivos reales."""
    municipios = pd.read_csv(DATA_CLEAN / "municipios_coordenadas.csv", dtype={"cod_dane": str})
    destinos = pd.read_csv(DATA_CLEAN / "destinos_coordenadas.csv")
    matriz = pd.read_csv(DATA_CLEAN / "matriz_tiempos.csv", dtype={"origen": str, "destino": str})
    return municipios, destinos, matriz


def construir_matriz_tiempos_dict(matriz, municipios, destinos):
    """
    Construye dict {(origen, destino): minutos} validando todos los trayectos
    necesarios ANTES de resolver (P6):
      - presencia de todos los pares municipio-municipio y municipio-destino,
      - valores numéricos, finitos y no negativos,
      - sin claves duplicadas contradictorias.
    Permite tiempo 0 sólo en la diagonal (municipio consigo mismo).
    Lanza ValueError identificando los pares problemáticos. No usa .get(...,0).
    """
    nodos = municipios["cod_dane"].tolist()
    dest_ids = destinos["id_destino"].tolist()

    # 1. claves duplicadas contradictorias
    dup = matriz.groupby(["origen", "destino"])["minutos"].nunique()
    contradictorias = dup[dup > 1]
    if len(contradictorias) > 0:
        pares = contradictorias.index.tolist()[:10]
        raise ValueError(
            "Matriz de tiempos con claves duplicadas contradictorias: {} pares "
            "(ej. {}).".format(len(contradictorias), pares)
        )

    tiempos = {}
    invalidos = []
    for _, row in matriz.iterrows():
        o, d, val = row["origen"], row["destino"], row["minutos"]
        if pd.isna(val) or not np.isfinite(val) or val < 0:
            invalidos.append((o, d, val))
        else:
            tiempos[(o, d)] = float(val)
    if invalidos:
        raise ValueError(
            "Matriz de tiempos con valores no válidos (NaN/inf/negativos): {} pares "
            "(ej. {}).".format(len(invalidos), invalidos[:10])
        )

    # 2. presencia de todos los pares requeridos
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
            "Tiempos faltantes en la matriz (P6): {} pares sin tiempo definido "
            "(ej. {}). No se asumen 0 para no favorecer ubicaciones artificialmente."
            .format(len(faltantes), faltantes[:10])
        )

    # diagonal: tiempo 0 permitido (no obligatorio en la matriz)
    for o in nodos:
        tiempos.setdefault((o, o), 0.0)

    return tiempos


def cargar_paquete_solver(id_escenario="2024_Obase_Cbase_M80_20", anio=2024):
    """Carga el paquete de datos del adaptador de Alejandro para el solver."""
    return preparar_para_solver(id_escenario, anio)


# =============================================================================
# PESOS DE DESTINOS (P1): reparto dentro de cada grupo, configurable y validado
# =============================================================================

def construir_pesos_destinos(destinos, pct_nac, pct_exp,
                             pesos_internos_nac=None, pesos_internos_exp=None):
    """
    Devuelve dict {id_destino: peso_global} donde peso_global = cuota_grupo * peso_interno.
    Por defecto el reparto interno es igual dentro de cada grupo.

    Valida:
      - cuotas nacional+exportación suman 1,
      - pesos finitos y no negativos,
      - pesos internos de cada grupo ACTIVO (cuota > 0) suman 1,
      - un grupo con cuota positiva tiene al menos un destino válido.
    """
    if not (np.isfinite(pct_nac) and np.isfinite(pct_exp)):
        raise ValueError("Cuotas nacional/exportación no finitas.")
    if pct_nac < 0 or pct_exp < 0:
        raise ValueError("Cuotas nacional/exportación negativas.")
    if abs(pct_nac + pct_exp - 1.0) > 1e-9:
        raise ValueError("pct_nacional + pct_exportacion debe sumar 1 (es {}).".format(pct_nac + pct_exp))

    disponibles = set(destinos["id_destino"].tolist())
    dest_nac = [d for d in DESTINOS_NACIONALES if d in disponibles]
    dest_exp = [d for d in DESTINOS_EXPORTACION if d in disponibles]

    def _pesos_grupo(dest_grupo, cuota, pesos_internos, nombre):
        if cuota <= 0:
            return {}  # grupo inactivo: no aporta destinos
        if not dest_grupo:
            raise ValueError(
                "El grupo {} tiene cuota {} > 0 pero no hay destinos válidos.".format(nombre, cuota)
            )
        if pesos_internos is None:
            pin = {d: 1.0 / len(dest_grupo) for d in dest_grupo}
        else:
            pin = {d: float(pesos_internos[d]) for d in dest_grupo if d in pesos_internos}
            if set(pin) != set(dest_grupo):
                raise ValueError(
                    "Pesos internos de {} incompletos: faltan {}.".format(
                        nombre, set(dest_grupo) - set(pin))
                )
            for d, p in pin.items():
                if not np.isfinite(p) or p < 0:
                    raise ValueError("Peso interno inválido en {}: {}={}.".format(nombre, d, p))
            s = sum(pin.values())
            if abs(s - 1.0) > 1e-9:
                raise ValueError(
                    "Pesos internos del grupo {} activo deben sumar 1 (suman {}).".format(nombre, s)
                )
        return {d: cuota * p for d, p in pin.items()}

    pesos = {}
    pesos.update(_pesos_grupo(dest_nac, pct_nac, pesos_internos_nac, "nacional"))
    pesos.update(_pesos_grupo(dest_exp, pct_exp, pesos_internos_exp, "exportación"))
    return pesos


# =============================================================================
# MODELO OR-TOOLS (flujo explícito; tramo satélite->central obligatorio)
# =============================================================================

def resolver_ubicacion(paquete, municipios, destinos, tiempos, k=5, lam=0.5,
                       modo="libre", pesos_internos_nac=None, pesos_internos_exp=None,
                       tiempo_limite_s=120, gap_relativo=0.0, tol_int=1e-6):
    """
    Resuelve la ubicación de central y k satélites con flujo explícito.

    modo:
      "libre"  -> exactamente k satélites, asignación municipal sin restricción de zona.
      "zonas"  -> un satélite por zona (k debe igualar el número de zonas); cada
                  municipio se asigna a un satélite de SU misma zona. El solver elige
                  la ubicación dentro de cada zona (los centros de zonas.csv no se fuerzan).

    Variables x, y BINARIAS; z, w relajadas a [0,1] (p-mediana con relajación LP
    integral); f continua. Antes de construir las asignaciones se verifica
    integralidad de x, y, z, w (tol_int) y la estructura (un satélite por municipio y
    abierto; cada satélite abierto enlaza con la única central; coherencia
    flujo/costos). Si hay fracciones o incoherencias se lanza ValueError (no se
    redondea en silencio); garantiza una asignación integral válida con objetivo
    verificado contra el solver.

    gap_relativo=0.0 -> óptimo certificado. tiempo_limite_s acota el tiempo del solver.

    Retorna dict con estado, central, satélites, asignaciones, flujos, costos (A, B,
    tres tramos y objetivo) y 'diagnostico' (solver, estado, objetivo, mejor_cota,
    gap_efectivo con su fórmula, tiempo_s, gap_solicitado y si fue aceptado). El tramo
    satélite->central SIEMPRE está en el objetivo.
    """
    # SCIP resuelve este MIP lineal mucho más rápido que CBC; CBC como respaldo.
    solver = pywraplp.Solver.CreateSolver("SCIP") or pywraplp.Solver.CreateSolver("CBC")
    if not solver:
        raise RuntimeError("No se pudo crear el solver (SCIP/CBC)")

    zonas = paquete.zonas.copy()
    excedente_mun = paquete.excedente_municipio.copy()
    pct_nac = paquete.pct_nacional
    pct_exp = paquete.pct_exportacion

    mun_a_zona = dict(zip(zonas["cod_dane"], zonas["zona"]))
    cod_mun_all = municipios["cod_dane"].tolist()

    # q_m: excedente conocido por municipio (pendientes ya excluidos por el adaptador)
    q = {m: 0.0 for m in cod_mun_all}
    for _, row in excedente_mun.iterrows():
        q[row["cod_dane"]] = float(row["excedente_t"])
    Q = sum(q.values())  # excedente total conocido (cota válida del flujo)

    # --- validación de modo territorial ---
    zonas_unicas = sorted(zonas["zona"].dropna().unique().tolist())
    if modo == "zonas":
        # correspondencia completa municipio-zona
        sin_zona = [m for m in cod_mun_all if m not in mun_a_zona or pd.isna(mun_a_zona.get(m))]
        if sin_zona:
            raise ValueError("Municipios sin zona asignada: {}.".format(sin_zona[:10]))
        if k != len(zonas_unicas):
            raise ValueError(
                "Modo 'zonas' exige exactamente un satélite por zona: k={} pero hay "
                "{} zonas {}. Ajusta k={}.".format(k, len(zonas_unicas), zonas_unicas, len(zonas_unicas))
            )
    elif modo != "libre":
        raise ValueError("modo debe ser 'libre' o 'zonas', no '{}'.".format(modo))

    # --- pesos de destinos (P1) ---
    pesos_dest = construir_pesos_destinos(
        destinos, pct_nac, pct_exp, pesos_internos_nac, pesos_internos_exp
    )

    C = cod_mun_all
    S = cod_mun_all

    # --- variables ---
    # x (central) e y (satélite) son BINARIAS: son las decisiones combinatorias.
    # z (asignación municipio->satélite) y w (enlace satélite->central) se relajan a
    # [0,1]: fijadas x,y, el subproblema es una p-mediana cuya relajación LP es
    # integral (cada municipio va al satélite abierto más barato; cada satélite a la
    # única central abierta). Esto acelera y estabiliza la resolución. NO se confía
    # ciegamente: tras resolver se VERIFICA integralidad (tol_int) y, si algún z o w
    # resultara fraccionario, se lanza error (no se redondea en silencio).
    x = {c: solver.BoolVar("x_{}".format(c)) for c in C}
    y = {s: solver.BoolVar("y_{}".format(s)) for s in S}
    z = {(m, s): solver.NumVar(0.0, 1.0, "z_{}_{}".format(m, s)) for m in cod_mun_all for s in S}
    w = {(s, c): solver.NumVar(0.0, 1.0, "w_{}_{}".format(s, c)) for s in S for c in C}
    f = {(s, c): solver.NumVar(0.0, solver.infinity(), "f_{}_{}".format(s, c)) for s in S for c in C}

    # --- restricciones ---
    solver.Add(solver.Sum([x[c] for c in C]) == 1)                       # R1
    solver.Add(solver.Sum([y[s] for s in S]) == k)                       # R2

    for m in cod_mun_all:                                                # R3
        solver.Add(solver.Sum([z[(m, s)] for s in S]) == 1)
        for s in S:
            solver.Add(z[(m, s)] <= y[s])

    for s in S:                                                          # R4
        solver.Add(solver.Sum([w[(s, c)] for c in C]) == y[s])
        for c in C:
            solver.Add(w[(s, c)] <= x[c])

    # volumen recibido por cada satélite (expresión reutilizada)
    recibido = {s: solver.Sum([q[m] * z[(m, s)] for m in cod_mun_all]) for s in S}

    # R5: conservación de flujo (todo lo recibido por s sale hacia alguna central)
    for s in S:
        solver.Add(solver.Sum([f[(s, c)] for c in C]) == recibido[s])

    # R6: vinculación del flujo (sólo por enlaces abiertos; Q es cota válida)
    for s in S:
        for c in C:
            solver.Add(f[(s, c)] <= Q * w[(s, c)])

    # modo zonas: un satélite por zona + asignación dentro de la zona
    if modo == "zonas":
        for zn in zonas_unicas:
            s_en_zona = [s for s in S if mun_a_zona.get(s) == zn]
            solver.Add(solver.Sum([y[s] for s in s_en_zona]) == 1)
        for m in cod_mun_all:
            zm = mun_a_zona.get(m)
            for s in S:
                if mun_a_zona.get(s) != zm:
                    solver.Add(z[(m, s)] == 0)

    # --- costos (expresiones lineales) ---
    # A1: recolección municipio->satélite
    A1 = solver.Sum([q[m] * tiempos[(m, s)] * z[(m, s)]
                     for m in cod_mun_all for s in S])
    # A2: satélite->central (flujo explícito; NO oferta[s])
    A2 = solver.Sum([f[(s, c)] * tiempos[(s, c)] for s in S for c in C])
    A = A1 + A2

    # B: central->destinos. Una sola central lleva TODO el volumen conocido Q.
    #    costo_unitario[c] = sum_d peso_global[d] * t[c,d]; B = Q * sum_c x[c]*costo_unitario[c]
    costo_unit_dist = {c: sum(peso * tiempos[(c, d)] for d, peso in pesos_dest.items())
                       for c in C}
    B = solver.Sum([x[c] * costo_unit_dist[c] * Q for c in C])

    solver.Minimize(lam * A + (1 - lam) * B)

    if tiempo_limite_s and tiempo_limite_s > 0:
        solver.SetTimeLimit(int(tiempo_limite_s * 1000))  # ms
    gap_aceptado, gap_detalle = _configurar_gap(solver, gap_relativo)

    import time as _time
    _t0 = _time.time()
    status = solver.Solve()
    wall_s = round(_time.time() - _t0, 2)
    estado = _ESTADOS.get(status, "DESCONOCIDO")

    # diagnóstico del solver (se devuelve siempre, haya o no solución)
    try:
        cota = solver.Objective().BestBound()
    except Exception:
        cota = None
    diagnostico = {
        "solver": solver.SolverVersion(),
        "status": estado,
        "tiempo_s": wall_s,
        "gap_solicitado": gap_relativo,
        "gap_aceptado": gap_aceptado,
        "gap_detalle": gap_detalle,
    }

    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        d = {"status": estado, "modo": modo, "k": k, "lambda": lam}
        d.update({"diagnostico": diagnostico})
        return d

    objetivo_solver = solver.Objective().Value()
    # Brecha efectiva: |objetivo - mejor_cota| / (|objetivo| + 1e-9).
    # (MIP de minimización: mejor_cota <= objetivo; la brecha mide cuánto podría bajar.)
    if cota is not None and np.isfinite(cota):
        gap_efectivo = abs(objetivo_solver - cota) / (abs(objetivo_solver) + 1e-9)
    else:
        gap_efectivo = None
    diagnostico["objetivo"] = objetivo_solver
    diagnostico["mejor_cota"] = cota
    diagnostico["gap_efectivo"] = gap_efectivo
    diagnostico["gap_efectivo_formula"] = "|obj - mejor_cota| / (|obj| + 1e-9)"

    # ---------------------------------------------------------------------
    # VERIFICACIÓN DE INTEGRALIDAD Y ESTRUCTURA (antes de construir asignaciones)
    # No se redondea en silencio: si algo es fraccionario o incoherente, se lanza error.
    # ---------------------------------------------------------------------
    def _es_binario(v):
        val = v.solution_value()
        return (abs(val) <= tol_int) or (abs(val - 1.0) <= tol_int)

    fraccionarias = []
    for nombre_var, dic in (("x", x), ("y", y), ("z", z), ("w", w)):
        for clave, var in dic.items():
            if not _es_binario(var):
                fraccionarias.append((nombre_var, clave, round(var.solution_value(), 6)))
    if fraccionarias:
        raise ValueError(
            "Solución con variables binarias fraccionarias (tol_int={}): {} casos "
            "(ej. {}). No se redondea; use binarias o recuperación válida."
            .format(tol_int, len(fraccionarias), fraccionarias[:8])
        )

    def _uno(v):
        return v.solution_value() > 0.5

    # central única y abierta
    centrales = [c for c in C if _uno(x[c])]
    if len(centrales) != 1:
        raise ValueError("Se esperaba exactamente 1 central abierta, hay {}.".format(len(centrales)))
    central = centrales[0]

    # satélites abiertos = k
    satelites = [s for s in S if _uno(y[s])]
    if len(satelites) != k:
        raise ValueError("Se esperaban {} satélites abiertos, hay {}.".format(k, len(satelites)))

    # cada municipio: exactamente un satélite, y ese satélite está abierto
    asign_m_s = []
    for m in cod_mun_all:
        sats_m = [s for s in S if _uno(z[(m, s)])]
        if len(sats_m) != 1:
            raise ValueError("Municipio {} asignado a {} satélites (esperado 1).".format(m, len(sats_m)))
        s_m = sats_m[0]
        if not _uno(y[s_m]):
            raise ValueError("Municipio {} asignado a satélite cerrado {}.".format(m, s_m))
        asign_m_s.append((m, s_m))

    # cada satélite abierto enlaza con la única central abierta; satélite cerrado no enlaza
    asign_s_c = []
    for s in S:
        cents_s = [c for c in C if _uno(w[(s, c)])]
        if _uno(y[s]):
            if cents_s != [central]:
                raise ValueError(
                    "Satélite abierto {} enlaza con {} (esperado [{}]).".format(s, cents_s, central))
            asign_s_c.append((s, central))
        else:
            if cents_s:
                raise ValueError("Satélite cerrado {} tiene enlace {}.".format(s, cents_s))

    flujos = {(s, c): f[(s, c)].solution_value()
              for s in S for c in C if f[(s, c)].solution_value() > tol_int}

    # --- costos reportados (recalculados desde la solución) ---
    A1_val = sum(q[m] * tiempos[(m, s)] for (m, s) in asign_m_s)
    A2_val = sum(vol * tiempos[(s, c)] for (s, c), vol in flujos.items())
    A_val = A1_val + A2_val
    B_val = costo_unit_dist[central] * Q
    objetivo_val = lam * A_val + (1 - lam) * B_val

    # coherencia asignaciones<->flujos: lo recibido por cada satélite = lo que envía
    recibido_por_sat = {}
    for (m, s) in asign_m_s:
        recibido_por_sat[s] = recibido_por_sat.get(s, 0.0) + q[m]
    enviado_por_sat = {}
    for (s, c), vol in flujos.items():
        enviado_por_sat[s] = enviado_por_sat.get(s, 0.0) + vol
    tol_flujo = max(1.0, 1e-6 * (Q + 1.0))
    for s in satelites:
        if abs(recibido_por_sat.get(s, 0.0) - enviado_por_sat.get(s, 0.0)) > tol_flujo:
            raise ValueError(
                "Incoherencia flujo/asignación en satélite {}: recibido {:.3f} != enviado {:.3f}."
                .format(s, recibido_por_sat.get(s, 0.0), enviado_por_sat.get(s, 0.0))
            )
    # coherencia objetivo recalculado vs solver
    tol_obj = max(1.0, 1e-5 * (abs(objetivo_solver) + 1.0))
    if abs(objetivo_val - objetivo_solver) > tol_obj:
        raise ValueError(
            "Objetivo recalculado {:.3f} difiere del solver {:.3f} (tol {:.3f})."
            .format(objetivo_val, objetivo_solver, tol_obj)
        )

    cen_row = municipios[municipios["cod_dane"] == central]
    cen_nombre = cen_row["municipio"].iloc[0] if not cen_row.empty else central
    cen_zona = mun_a_zona.get(central, "N/A")

    satelite_info = []
    for s in satelites:
        s_row = municipios[municipios["cod_dane"] == s]
        s_nombre = s_row["municipio"].iloc[0] if not s_row.empty else s
        es_centro = zonas[zonas["cod_dane"] == s]["es_centro_zona"]
        satelite_info.append({
            "cod_dane": s,
            "nombre": s_nombre,
            "zona": mun_a_zona.get(s, "N/A"),
            "es_centro": int(es_centro.iloc[0]) if not es_centro.empty else 0,
        })

    return {
        "status": estado,
        "modo": modo,
        "central": central,
        "central_nombre": cen_nombre,
        "central_zona": cen_zona,
        "satelites": satelite_info,
        "satelites_cods": satelites,
        "asignaciones_municipio_satelite": asign_m_s,
        "asignaciones_satelite_central": asign_s_c,
        "flujos_satelite_central": flujos,
        "volumen_total_conocido": Q,
        # tres tramos
        "costo_recoleccion": A1_val,          # A1
        "costo_satelite_central": A2_val,     # A2
        "costo_central_destinos": B_val,      # B
        # componentes del objetivo
        "A": A_val,                           # A = A1 + A2
        "B": B_val,                           # B
        "costo_total": objetivo_val,          # lam*A + (1-lam)*B (recalculado)
        "objetivo_solver": objetivo_solver,   # valor del solver (debe coincidir)
        "k": k,
        "lambda": lam,
        "pct_nacional": pct_nac,
        "pct_exportacion": pct_exp,
        "cobertura": paquete.cobertura_oferta_pct,
        "cobertura_parcial": paquete.cobertura_parcial,
        "advertencias": paquete.advertencias,
        "diagnostico": diagnostico,
    }


# =============================================================================
# SOLUCIONES NO DOMINADAS (barrido de lambda sobre A y B) — P4
# =============================================================================

def filtrar_no_dominados(df, tol_rel=TOL_PARETO_REL):
    """
    Devuelve las soluciones NO DOMINADAS en (A, B), eliminando duplicados y puntos
    dominados con tolerancia relativa documentada (tol_rel).

    Un punto (A, B) domina a (A', B') si A <= A' y B <= B' con al menos una
    desigualdad estricta (fuera de tolerancia). No se afirma que el barrido de
    lambda recupere toda la frontera: son 'soluciones no dominadas encontradas'.
    """
    if df.empty:
        return df
    pts = df.reset_index(drop=True)
    escala_A = max(pts["A"].abs().max(), 1.0)
    escala_B = max(pts["B"].abs().max(), 1.0)

    def domina(i, j):
        # i domina a j
        le = (pts.loc[i, "A"] <= pts.loc[j, "A"] + tol_rel * escala_A and
              pts.loc[i, "B"] <= pts.loc[j, "B"] + tol_rel * escala_B)
        lt = (pts.loc[i, "A"] < pts.loc[j, "A"] - tol_rel * escala_A or
              pts.loc[i, "B"] < pts.loc[j, "B"] - tol_rel * escala_B)
        return le and lt

    keep = []
    for j in pts.index:
        if not any(domina(i, j) for i in pts.index if i != j):
            keep.append(j)
    res = pts.loc[keep].copy()

    # deduplicar puntos casi iguales en (A, B)
    res = res.sort_values(["A", "B"]).reset_index(drop=True)
    dedup_idx = []
    for i in res.index:
        if not dedup_idx:
            dedup_idx.append(i)
            continue
        p = res.loc[dedup_idx[-1]]
        if (abs(res.loc[i, "A"] - p["A"]) > tol_rel * escala_A or
                abs(res.loc[i, "B"] - p["B"]) > tol_rel * escala_B):
            dedup_idx.append(i)
    return res.loc[dedup_idx].reset_index(drop=True)


def calcular_frontera_pareto(paquete, municipios, destinos, tiempos,
                             k=5, lambdas=None, modo="libre",
                             pesos_internos_nac=None, pesos_internos_exp=None,
                             tiempo_limite_s=120, gap_relativo=0.0):
    """
    Barre lambda y devuelve las SOLUCIONES NO DOMINADAS encontradas en (A, B),
    coherentes con el objetivo λ·A + (1-λ)·B.
    """
    if lambdas is None:
        lambdas = [i / 10 for i in range(11)]
    datos = []
    for lam in lambdas:
        res = resolver_ubicacion(
            paquete, municipios, destinos, tiempos,
            k=k, lam=lam, modo=modo,
            pesos_internos_nac=pesos_internos_nac, pesos_internos_exp=pesos_internos_exp,
            tiempo_limite_s=tiempo_limite_s, gap_relativo=gap_relativo,
        )
        if res["status"] in ("OPTIMAL", "FEASIBLE"):
            datos.append({
                "lambda": lam,
                "central": "{} ({})".format(res["central_nombre"], res["central"]),
                "zona_central": res["central_zona"],
                "A": res["A"],          # recolección + satélite-central
                "B": res["B"],          # central-destinos
                "costo_recoleccion": res["costo_recoleccion"],
                "costo_satelite_central": res["costo_satelite_central"],
                "costo_central_destinos": res["costo_central_destinos"],
                "costo_total": res["costo_total"],
                "status": res["status"],
            })
    df = pd.DataFrame(datos)
    if not df.empty:
        df = filtrar_no_dominados(df)
    return df


# =============================================================================
# ESTABILIDAD (parametrizada: año, consumo, mezcla, modo, k, lambda) — P (fijos 2024)
# =============================================================================

def _id_escenario(anio, oferta, consumo, mezcla):
    return "{}_O{}_C{}_M{}".format(anio, oferta, consumo, mezcla)


def calcular_estabilidad(municipios, destinos, tiempos, anio,
                         consumo="base", mezcla="80_20", modo="libre",
                         k=5, lam=0.5, ofertas=("bajo", "base", "alto"),
                         pesos_internos_nac=None, pesos_internos_exp=None,
                         tiempo_limite_s=120, gap_relativo=0.0):
    """
    Compara oferta baja/base/alta para un MISMO año, consumo, mezcla, modo, k y lambda.
    Reporta el estado del solver de cada escenario y los que falten o fallen; no usa
    except/continue silencioso. NO llama 'óptima' a una solución sólo FEASIBLE.
    """
    filas = []
    faltantes = []
    for of in ofertas:
        idesc = _id_escenario(anio, of, consumo, mezcla)
        try:
            pkg = preparar_para_solver(idesc, anio)
        except Exception as e:
            faltantes.append({"escenario": idesc, "motivo": "no_disponible: {}".format(e)})
            filas.append({"escenario": idesc, "oferta": of, "consumo": consumo,
                          "central": None, "status": "NO_DISPONIBLE",
                          "A": np.nan, "B": np.nan, "costo_total": np.nan,
                          "cobertura": np.nan})
            continue
        res = resolver_ubicacion(pkg, municipios, destinos, tiempos, k=k, lam=lam,
                                 modo=modo, pesos_internos_nac=pesos_internos_nac,
                                 pesos_internos_exp=pesos_internos_exp,
                                 tiempo_limite_s=tiempo_limite_s, gap_relativo=gap_relativo)
        if res["status"] in ("OPTIMAL", "FEASIBLE"):
            filas.append({
                "escenario": idesc, "oferta": pkg.escenario_oferta, "consumo": pkg.escenario_consumo,
                "central": "{} ({})".format(res["central_nombre"], res["central"]),
                "status": res["status"], "A": res["A"], "B": res["B"],
                "costo_total": res["costo_total"], "cobertura": pkg.cobertura_oferta_pct,
            })
        else:
            filas.append({"escenario": idesc, "oferta": of, "consumo": consumo,
                          "central": None, "status": res["status"],
                          "A": np.nan, "B": np.nan, "costo_total": np.nan,
                          "cobertura": pkg.cobertura_oferta_pct})
    df = pd.DataFrame(filas)
    df.attrs["faltantes"] = faltantes
    df.attrs["anio"] = anio
    return df


# =============================================================================
# COMPARACIÓN LIBRE vs ZONAS (mismas entradas)
# =============================================================================

def comparar_configuraciones(paquete, municipios, destinos, tiempos, k=5, lam=0.5,
                             pesos_internos_nac=None, pesos_internos_exp=None,
                             tiempo_limite_s=120, gap_relativo=0.0):
    """
    Resuelve el MISMO escenario (año, oferta, consumo, mezcla, lambda, k) en modo
    libre y en modo zonas, para comparar con entradas iguales.
    """
    out = {}
    for modo in ("libre", "zonas"):
        res = resolver_ubicacion(paquete, municipios, destinos, tiempos, k=k, lam=lam,
                                 modo=modo, pesos_internos_nac=pesos_internos_nac,
                                 pesos_internos_exp=pesos_internos_exp,
                                 tiempo_limite_s=tiempo_limite_s, gap_relativo=gap_relativo)
        out[modo] = res
    return out


# =============================================================================
# EJECUCIÓN PRINCIPAL
# =============================================================================

def main():
    print("=" * 70)
    print("MODELO DE OPTIMIZACIÓN LOGÍSTICA — FLUJO SATÉLITE-CENTRAL EXPLÍCITO")
    print("=" * 70)
    print()

    municipios, destinos, matriz_tiempos = cargar_datos_reales()
    tiempos = construir_matriz_tiempos_dict(matriz_tiempos, municipios, destinos)
    print("Municipios: {} | Destinos: {} | Entradas matriz: {}".format(
        len(municipios), len(destinos), len(matriz_tiempos)))

    paquete = cargar_paquete_solver("2024_Obase_Cbase_M80_20", 2024)
    print("Escenario: {} | Oferta={} Consumo={} Nac={:.0%} Exp={:.0%}".format(
        paquete.id_escenario, paquete.escenario_oferta, paquete.escenario_consumo,
        paquete.pct_nacional, paquete.pct_exportacion))
    print("Cobertura: {}% (parcial={}) | Volumen conocido: {:,.1f} t".format(
        paquete.cobertura_oferta_pct, paquete.cobertura_parcial,
        paquete.excedente_municipio["excedente_t"].sum()))
    print()

    print("--- Comparación de configuraciones (k=5, lambda=0.5) ---")
    comp = comparar_configuraciones(paquete, municipios, destinos, tiempos, k=5, lam=0.5)
    for modo, res in comp.items():
        if res["status"] not in ("OPTIMAL", "FEASIBLE"):
            print("  [{}] estado: {}".format(modo, res["status"]))
            continue
        print("  [{}] estado={} central={} (zona {})".format(
            modo, res["status"], res["central_nombre"], res["central_zona"]))
        print("        A1 recolección = {:,.0f} | A2 sat->central = {:,.0f} | "
              "B central->dest = {:,.0f}".format(
                  res["costo_recoleccion"], res["costo_satelite_central"],
                  res["costo_central_destinos"]))
        print("        A = {:,.0f} | B = {:,.0f} | objetivo = {:,.0f} "
              "(solver={:,.0f})".format(res["A"], res["B"], res["costo_total"],
                                        res["objetivo_solver"]))
        print("        satélites: {}".format(
            ", ".join("{} ({})".format(s["nombre"], s["zona"]) for s in res["satelites"])))
    print()

    print("--- Soluciones no dominadas encontradas (barrido de lambda, modo libre) ---")
    df_pareto = calcular_frontera_pareto(paquete, municipios, destinos, tiempos, k=5, modo="libre")
    print(df_pareto[["lambda", "central", "A", "B", "costo_total"]].to_string(index=False))
    print()

    print("--- Estabilidad (año 2024, consumo base, mezcla 80_20, modo libre) ---")
    df_estab = calcular_estabilidad(municipios, destinos, tiempos, anio=2024,
                                    consumo="base", mezcla="80_20", modo="libre", k=5)
    print(df_estab[["escenario", "oferta", "central", "status", "A", "B", "costo_total"]].to_string(index=False))
    if df_estab.attrs.get("faltantes"):
        print("Escenarios faltantes:", df_estab.attrs["faltantes"])

    print()
    print("=" * 70)
    print("MODELO COMPLETADO")
    print("=" * 70)


if __name__ == "__main__":
    main()
