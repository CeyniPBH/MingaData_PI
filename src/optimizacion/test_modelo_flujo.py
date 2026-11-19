"""
Pruebas del modelo de optimización logística con flujo satélite-central explícito.

Detectan los errores originales de d37d663:
  - A2 usaba oferta[s] en vez del volumen recibido.
  - La conservación usaba oferta[s] como salida.
  - Pareto no coincidía con los componentes del objetivo.
  - calcular_estabilidad() usaba escenarios fijos de 2024.
  - usar_flujo / usar_satelite_central permitían desactivar el tramo.
  - Tiempos faltantes se ocultaban con .get(..., 0).

Ejecutar: python -m pytest src/optimizacion/test_modelo_flujo.py -q
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "optimizacion"))
sys.path.insert(0, str(ROOT / "src" / "arendonc2"))

import modelo_real as M  # noqa: E402
from ortools.linear_solver import pywraplp  # noqa: E402



# ---------------------------------------------------------------------------
# Caso pequeño controlado: fijamos ubicaciones y asignaciones para comprobar
# el CÁLCULO de flujo y costo, sin depender de dónde decida ubicarse el solver.
# ---------------------------------------------------------------------------

def _solver_caso_fijo():
    """
    3 municipios A, B, C. A es satélite, recibe de sí mismo (10 t) y de B (90 t).
    C es la central. t[A,C] = 20 min. Verificamos que el flujo A->C = 100 t y
    el costo del tramo = 2000 t·min, con el modelo lineal (f, w continuos/binarios).
    """
    solver = pywraplp.Solver.CreateSolver("SCIP") or pywraplp.Solver.CreateSolver("CBC")
    q = {"A": 10.0, "B": 90.0, "C": 0.0}
    Q = sum(q.values())
    muni = ["A", "B", "C"]
    # tiempos
    t = {("A", "A"): 0, ("B", "B"): 0, ("C", "C"): 0,
         ("A", "C"): 20, ("C", "A"): 20,
         ("B", "A"): 5, ("A", "B"): 5, ("B", "C"): 7, ("C", "B"): 7}

    f = {(s, c): solver.NumVar(0, solver.infinity(), f"f_{s}_{c}") for s in muni for c in muni}
    w = {(s, c): solver.BoolVar(f"w_{s}_{c}") for s in muni for c in muni}
    z = {(m, s): solver.BoolVar(f"z_{m}_{s}") for m in muni for s in muni}

    # Fijar: A y B asignados al satélite A; C asignado al satélite C.
    solver.Add(z[("A", "A")] == 1)
    solver.Add(z[("B", "A")] == 1)
    solver.Add(z[("C", "C")] == 1)
    for m in muni:
        for s in muni:
            if (m, s) not in (("A", "A"), ("B", "A"), ("C", "C")):
                solver.Add(z[(m, s)] == 0)
    # Satélite A -> central C; satélite C no envía (0 recibido)
    solver.Add(w[("A", "C")] == 1)
    for (s, c) in list(w):
        if (s, c) != ("A", "C"):
            solver.Add(w[(s, c)] == 0)

    # Conservación y vinculación (como en el modelo real)
    for s in muni:
        recibido = solver.Sum([q[m] * z[(m, s)] for m in muni])
        solver.Add(solver.Sum([f[(s, c)] for c in muni]) == recibido)
    for s in muni:
        for c in muni:
            solver.Add(f[(s, c)] <= Q * w[(s, c)])

    costo = solver.Sum([f[(s, c)] * t.get((s, c), 0) for s in muni for c in muni])
    solver.Minimize(costo)
    solver.Solve()
    return f, costo, solver


def test_flujo_recibido_suma_correcta():
    """A recibe 10 t (propias) + 90 t (de B) = 100 t que salen hacia la central."""
    f, costo, solver = _solver_caso_fijo()
    flujo_AC = f[("A", "C")].solution_value()
    assert abs(flujo_AC - 100.0) < 1e-6, f"flujo A->C = {flujo_AC}, esperado 100"


def test_costo_segundo_tramo():
    """Si A->C tarda 20 min y pasan 100 t, el costo del tramo es 2000 t·min."""
    f, costo, solver = _solver_caso_fijo()
    assert abs(solver.Objective().Value() - 2000.0) < 1e-6


def test_flujo_por_enlaces_cerrados_es_cero():
    """Todo enlace distinto de A->C debe transportar 0 t."""
    f, costo, solver = _solver_caso_fijo()
    for (s, c), var in f.items():
        if (s, c) != ("A", "C"):
            assert var.solution_value() < 1e-6, f"flujo en enlace cerrado {s}->{c}"


# ---------------------------------------------------------------------------
# Modelo real con datos de Alejandro
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def base():
    mun, dst, mz = M.cargar_datos_reales()
    tiempos = M.construir_matriz_tiempos_dict(mz, mun, dst)
    pkg = M.cargar_paquete_solver("2024_Obase_Cbase_M80_20", 2024)
    return mun, dst, tiempos, pkg


def test_conservacion_flujo_global(base):
    """El flujo total satélite->central conserva el volumen conocido Q."""
    mun, dst, tiempos, pkg = base
    res = M.resolver_ubicacion(pkg, mun, dst, tiempos, k=5, lam=0.5, modo="libre")
    assert res["status"] in ("OPTIMAL", "FEASIBLE")
    total_flujo = sum(res["flujos_satelite_central"].values())
    assert abs(total_flujo - res["volumen_total_conocido"]) < 1.0


def test_conservacion_por_satelite(base):
    """Para cada satélite, lo que envía iguala lo que recibe de sus municipios."""
    mun, dst, tiempos, pkg = base
    res = M.resolver_ubicacion(pkg, mun, dst, tiempos, k=5, lam=0.5, modo="libre")
    q = {r["cod_dane"]: float(r["excedente_t"]) for _, r in pkg.excedente_municipio.iterrows()}
    recibido = {}
    for m, s in res["asignaciones_municipio_satelite"]:
        recibido[s] = recibido.get(s, 0.0) + q.get(m, 0.0)
    enviado = {}
    for (s, c), vol in res["flujos_satelite_central"].items():
        enviado[s] = enviado.get(s, 0.0) + vol
    for s in res["satelites_cods"]:
        assert abs(recibido.get(s, 0.0) - enviado.get(s, 0.0)) < 1.0, f"satélite {s}"


def test_objetivo_reportado_coincide_con_solver(base):
    """El costo total reportado coincide con el valor del solver."""
    mun, dst, tiempos, pkg = base
    res = M.resolver_ubicacion(pkg, mun, dst, tiempos, k=5, lam=0.5, modo="libre")
    assert abs(res["costo_total"] - res["objetivo_solver"]) < max(1.0, 1e-6 * abs(res["objetivo_solver"]))


def test_A_igual_recoleccion_mas_satelite_central(base):
    """A = costo recolección + costo satélite->central (componentes del objetivo)."""
    mun, dst, tiempos, pkg = base
    res = M.resolver_ubicacion(pkg, mun, dst, tiempos, k=5, lam=0.5, modo="libre")
    assert abs(res["A"] - (res["costo_recoleccion"] + res["costo_satelite_central"])) < 1.0
    assert abs(res["B"] - res["costo_central_destinos"]) < 1.0


def test_satelite_central_usa_volumen_no_oferta_s(base):
    """A2 debe reflejar el volumen que realmente pasa por cada satélite, no oferta[s].
    Si usara oferta[s] (excedente del propio municipio satélite), A2 sería mucho menor."""
    mun, dst, tiempos, pkg = base
    res = M.resolver_ubicacion(pkg, mun, dst, tiempos, k=5, lam=0.5, modo="libre")
    q = {r["cod_dane"]: float(r["excedente_t"]) for _, r in pkg.excedente_municipio.iterrows()}
    # A2 con el bug (oferta[s] del satélite)
    a2_bug = sum(q.get(s, 0.0) * tiempos[(s, c)] for (s, c) in res["asignaciones_satelite_central"])
    # A2 correcto (volumen recibido)
    a2_ok = res["costo_satelite_central"]
    # deben diferir (el satélite recibe de varios municipios, no solo de sí mismo)
    assert a2_ok > a2_bug + 1.0, "A2 no refleja el volumen recibido; parece usar oferta[s]"


def test_pareto_componentes_coinciden_con_optimizados(base):
    """Los A y B usados en Pareto coinciden con los del solver para cada lambda."""
    mun, dst, tiempos, pkg = base
    df = M.calcular_frontera_pareto(pkg, mun, dst, tiempos, k=5,
                                    lambdas=[0.0, 0.5, 1.0], modo="libre")
    assert not df.empty
    for _, row in df.iterrows():
        res = M.resolver_ubicacion(pkg, mun, dst, tiempos, k=5, lam=row["lambda"], modo="libre")
        assert abs(res["A"] - row["A"]) < 1.0
        assert abs(res["B"] - row["B"]) < 1.0


def test_pareto_no_dominados(base):
    """La frontera no contiene puntos dominados ni duplicados."""
    mun, dst, tiempos, pkg = base
    df = M.calcular_frontera_pareto(pkg, mun, dst, tiempos, k=5, modo="libre")
    pts = df[["A", "B"]].values
    for i in range(len(pts)):
        for j in range(len(pts)):
            if i != j:
                # ningún j domina a i
                domina = pts[j][0] <= pts[i][0] and pts[j][1] <= pts[i][1] and (
                    pts[j][0] < pts[i][0] or pts[j][1] < pts[i][1])
                assert not domina, "hay un punto dominado en la frontera"


def test_modo_zonas_un_satelite_por_zona(base):
    """Modo zonas: exactamente un satélite por cada una de las 5 zonas."""
    mun, dst, tiempos, pkg = base
    res = M.resolver_ubicacion(pkg, mun, dst, tiempos, k=5, lam=0.5, modo="zonas")
    assert res["status"] in ("OPTIMAL", "FEASIBLE")
    zonas_sat = [s["zona"] for s in res["satelites"]]
    assert len(zonas_sat) == 5
    assert len(set(zonas_sat)) == 5, f"zonas repetidas o faltantes: {zonas_sat}"


def test_modo_zonas_k_incompatible_falla(base):
    """Pedir k != nº de zonas en modo zonas debe fallar con error claro antes de resolver."""
    mun, dst, tiempos, pkg = base
    with pytest.raises(ValueError):
        M.resolver_ubicacion(pkg, mun, dst, tiempos, k=4, lam=0.5, modo="zonas")


def test_comparacion_usa_cinco_satelites_ambos_modos(base):
    """La comparación libre/zonas usa 5 satélites en ambos modos, mismas entradas."""
    mun, dst, tiempos, pkg = base
    comp = M.comparar_configuraciones(pkg, mun, dst, tiempos, k=5, lam=0.5)
    for modo in ("libre", "zonas"):
        assert comp[modo]["status"] in ("OPTIMAL", "FEASIBLE")
        assert len(comp[modo]["satelites"]) == 5


def test_estabilidad_anio_no_hardcodea_2024(base):
    """Elegir 2028 no debe cargar escenarios de 2024."""
    mun, dst, tiempos, pkg = base
    df = M.calcular_estabilidad(mun, dst, tiempos, anio=2028,
                                consumo="base", mezcla="80_20", modo="libre", k=5)
    assert df.attrs["anio"] == 2028
    assert (df["escenario"].str.startswith("2028_")).all()
    assert not (df["escenario"].str.startswith("2024_")).any()


def test_pendientes_no_aumentan_volumen(base):
    """El volumen conocido del solver no incluye productos pendientes."""
    mun, dst, tiempos, pkg = base
    res = M.resolver_ubicacion(pkg, mun, dst, tiempos, k=5, lam=0.5, modo="libre")
    # Q debe igualar la suma de excedente del adaptador (que ya excluye pendientes)
    Q_adaptador = pkg.excedente_municipio["excedente_t"].sum()
    assert abs(res["volumen_total_conocido"] - Q_adaptador) < 1.0


def test_tiempos_faltantes_error_claro():
    """Una matriz con un par faltante debe lanzar ValueError identificando el problema."""
    mun, dst, mz = M.cargar_datos_reales()
    # quitar un par off-diagonal REQUERIDO (dos municipios distintos) crea un hueco real
    off = mz[(mz["origen"] != mz["destino"]) & (mz["destino"].str.startswith("76"))].iloc[0]
    mask = ~((mz["origen"] == off["origen"]) & (mz["destino"] == off["destino"]))
    mz_incompleta = mz[mask].copy()
    with pytest.raises(ValueError) as exc:
        M.construir_matriz_tiempos_dict(mz_incompleta, mun, dst)
    assert "faltantes" in str(exc.value).lower() or "faltan" in str(exc.value).lower()


def test_tiempos_invalidos_error_claro():
    """Valores negativos o no numéricos en la matriz deben lanzar ValueError."""
    mun, dst, mz = M.cargar_datos_reales()
    mz_mala = mz.copy()
    mz_mala.loc[mz_mala.index[5], "minutos"] = -3.0
    with pytest.raises(ValueError) as exc:
        M.construir_matriz_tiempos_dict(mz_mala, mun, dst)
    assert "válid" in str(exc.value).lower() or "negativ" in str(exc.value).lower()


def test_pesos_destinos_validacion():
    """Pesos internos de un grupo activo deben sumar 1; cuotas nacional+exp = 1."""
    _, dst, _ = M.cargar_datos_reales()
    # cuotas que no suman 1
    with pytest.raises(ValueError):
        M.construir_pesos_destinos(dst, 0.8, 0.3)
    # pesos internos de nacional que no suman 1
    with pytest.raises(ValueError):
        M.construir_pesos_destinos(dst, 0.8, 0.2,
                                   pesos_internos_nac={"DEST_CALI": 0.5, "DEST_BOGOTA": 0.2, "DEST_MEDELLIN": 0.2})
    # reparto igual por defecto: nacional 0.8/3 cada uno
    pesos = M.construir_pesos_destinos(dst, 0.8, 0.2)
    assert abs(pesos["DEST_CALI"] - 0.8 / 3) < 1e-9
    assert abs(sum(pesos.values()) - 1.0) < 1e-9


def test_asignaciones_integrales_y_estructura(base):
    """Las asignaciones extraídas son íntegras: 42 municipios (uno cada uno), 5
    satélites, cada satélite abierto enlaza con la única central."""
    mun, dst, tiempos, pkg = base
    res = M.resolver_ubicacion(pkg, mun, dst, tiempos, k=5, lam=0.5, modo="libre")
    assert res["status"] in ("OPTIMAL", "FEASIBLE")
    # un satélite por municipio
    muni_asignados = [m for m, s in res["asignaciones_municipio_satelite"]]
    assert len(muni_asignados) == 42 and len(set(muni_asignados)) == 42
    # 5 enlaces satélite->central, todos a la misma central
    centrales_enlace = {c for s, c in res["asignaciones_satelite_central"]}
    assert len(res["asignaciones_satelite_central"]) == 5
    assert centrales_enlace == {res["central"]}


def test_diagnostico_completo(base):
    """El diagnóstico reporta solver, estado, objetivo, mejor cota, brecha, tiempo y
    tolerancia solicitada/aceptada."""
    mun, dst, tiempos, pkg = base
    res = M.resolver_ubicacion(pkg, mun, dst, tiempos, k=5, lam=0.5, modo="libre", gap_relativo=0.0)
    d = res["diagnostico"]
    for clave in ("solver", "status", "objetivo", "mejor_cota", "gap_efectivo",
                  "gap_efectivo_formula", "tiempo_s", "gap_solicitado", "gap_aceptado"):
        assert clave in d, "falta {} en diagnóstico".format(clave)
    # con gap solicitado 0 y OPTIMAL, la brecha efectiva es ~0
    assert d["gap_efectivo"] is not None and d["gap_efectivo"] < 1e-4


def test_municipios_excedente_cero(base):
    """Municipios con excedente conocido 0 se asignan igual (no rompen el modelo)."""
    mun, dst, tiempos, pkg = base
    q = {r["cod_dane"]: float(r["excedente_t"]) for _, r in pkg.excedente_municipio.iterrows()}
    ceros = [c for c, v in q.items() if v == 0.0]
    assert ceros, "se esperaban municipios con excedente 0 (p. ej. Cali)"
    res = M.resolver_ubicacion(pkg, mun, dst, tiempos, k=5, lam=0.5, modo="libre")
    asignados = {m for m, s in res["asignaciones_municipio_satelite"]}
    for c in ceros:
        assert c in asignados, "municipio con excedente 0 no asignado: {}".format(c)


def test_lambda_extremos(base):
    """Lambda=0 (sólo B) y lambda=1 (sólo A) resuelven con asignaciones íntegras."""
    mun, dst, tiempos, pkg = base
    for lam in (0.0, 1.0):
        res = M.resolver_ubicacion(pkg, mun, dst, tiempos, k=5, lam=lam, modo="libre")
        assert res["status"] in ("OPTIMAL", "FEASIBLE"), "lambda={}".format(lam)
        assert len(res["asignaciones_municipio_satelite"]) == 42
        # objetivo recalculado coincide con el del solver
        assert abs(res["costo_total"] - res["objetivo_solver"]) < max(1.0, 1e-5 * abs(res["objetivo_solver"]))


def test_empates_tiempos_iguales():
    """Con tiempos simétricos/empatados, la solución sigue siendo íntegra y factible.
    Caso pequeño controlado: 4 municipios equidistantes, k=1 satélite."""
    import pandas as pd
    from types import SimpleNamespace

    cods = ["76001", "76002", "76003", "76004"]
    nombres = ["A", "B", "C", "D"]
    zonas = pd.DataFrame({"cod_dane": cods, "municipio": nombres,
                          "zona": ["Z1"] * 4, "es_centro_zona": [0, 0, 0, 0]})
    exc = pd.DataFrame({"cod_dane": cods, "municipio": nombres, "zona": ["Z1"] * 4,
                        "excedente_t": [10.0, 10.0, 10.0, 10.0]})
    municipios = pd.DataFrame({"cod_dane": cods, "municipio": nombres,
                               "lat": [0, 0, 1, 1], "lon": [0, 1, 0, 1]})
    destinos = pd.DataFrame({"id_destino": ["DEST_CALI", "DEST_BUENAVENTURA"],
                             "nombre": ["Cali", "Buenaventura"], "lat": [0, 0], "lon": [0, 0]})
    # tiempos todos iguales (empate perfecto) salvo diagonal 0
    tiempos = {}
    for a in cods:
        for b in cods:
            tiempos[(a, b)] = 0.0 if a == b else 10.0
        for d in destinos["id_destino"]:
            tiempos[(a, d)] = 10.0
    pkg = SimpleNamespace(
        id_escenario="t", anio=2024, escenario_oferta="base", escenario_consumo="base",
        pct_nacional=0.8, pct_exportacion=0.2, excedente_municipio=exc,
        volumen_por_zona=pd.DataFrame({"zona": ["Z1"], "volumen_nacional": [32.0],
                                       "volumen_exportacion": [8.0], "excedente_t": [40.0]}),
        zonas=zonas, cobertura_oferta_pct=100.0, cobertura_parcial=False,
        alcance="test", advertencias=[])
    res = M.resolver_ubicacion(pkg, municipios, destinos, tiempos, k=1, lam=0.5, modo="libre")
    assert res["status"] in ("OPTIMAL", "FEASIBLE")
    assert len(res["asignaciones_municipio_satelite"]) == 4
    assert len(res["satelites"]) == 1
    # todo el volumen (40 t) llega a la central por el único satélite
    assert abs(sum(res["flujos_satelite_central"].values()) - 40.0) < 1e-6


def test_estado_infeasible_no_rompe():
    """Un escenario inexistente en estabilidad se reporta, no rompe la ejecución."""
    mun, dst, mz = M.cargar_datos_reales()
    tiempos = M.construir_matriz_tiempos_dict(mz, mun, dst)
    # año 2099 no existe -> debe aparecer como NO_DISPONIBLE, sin excepción
    df = M.calcular_estabilidad(mun, dst, tiempos, anio=2099, consumo="base",
                                mezcla="80_20", modo="libre", k=5)
    assert (df["status"] == "NO_DISPONIBLE").all()
    assert len(df.attrs["faltantes"]) == 3
