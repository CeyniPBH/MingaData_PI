"""
Verificacion de los CSV de optimizacion generados para el informe final.

No vuelve a resolver el MIP: valida estructura, coherencia de costos y
no-dominancia de la frontera de Pareto sobre los archivos ya generados.

Ejecuta:
    python src/optimizacion/test_resultados_opt.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SALIDA = ROOT / "data" / "results" / "opt"

ERRORES = []
EXITOS = []


def check(condicion, mensaje):
    if condicion:
        EXITOS.append("  [OK] {}".format(mensaje))
    else:
        ERRORES.append("  [FAIL] {}".format(mensaje))


def _leer(nombre, **kwargs):
    ruta = SALIDA / nombre
    check(ruta.exists(), "{} existe".format(nombre))
    if not ruta.exists():
        return pd.DataFrame()
    return pd.read_csv(ruta, encoding="utf-8-sig", **kwargs)


def _casi_igual(a, b, tol=1.0):
    return abs(float(a) - float(b)) <= tol


def _domina(a, b, tol_rel=1e-6):
    escala_a = max(abs(a["A"]), abs(b["A"]), 1.0)
    escala_b = max(abs(a["B"]), abs(b["B"]), 1.0)
    le = (a["A"] <= b["A"] + tol_rel * escala_a
          and a["B"] <= b["B"] + tol_rel * escala_b)
    lt = (a["A"] < b["A"] - tol_rel * escala_a
          or a["B"] < b["B"] - tol_rel * escala_b)
    return le and lt


def main():
    print("=" * 74)
    print("VERIFICACION DE RESULTADOS DE OPTIMIZACION PARA EL INFORME")
    print("=" * 74)

    ruta_meta = SALIDA / "metadata.json"
    check(ruta_meta.exists(), "metadata.json existe")
    meta = {}
    if ruta_meta.exists():
        meta = json.loads(ruta_meta.read_text(encoding="utf-8"))
        check("parametros" in meta, "metadata.json tiene parametros")
        check("salidas" in meta, "metadata.json tiene huellas de salida")
        check("solver" in meta and meta["solver"], "metadata.json registra el solver")

    k = int(meta.get("parametros", {}).get("k", 5))
    lam = float(meta.get("parametros", {}).get("lambda", 0.5))

    # 1. Barrido y frontera de Pareto
    print("\n--- 1. Barrido de lambda y frontera de Pareto ---")
    barrido = _leer("barrido_lambda_base.csv", dtype={"central_cod": str,
                                                      "satelites_cods": str})
    frontera = _leer("frontera_pareto_base.csv", dtype={"central_cod": str,
                                                        "satelites_cods": str})

    if not barrido.empty:
        check(len(barrido) == 11, "El barrido tiene 11 valores de lambda ({})".format(len(barrido)))
        check(barrido["lambda"].is_unique, "Los lambda del barrido no se repiten")
        check(barrido["lambda"].between(0, 1).all(), "Los lambda estan en [0, 1]")
        check(barrido["status"].isin(["OPTIMAL", "FEASIBLE"]).all(),
              "Todas las soluciones del barrido son OPTIMAL/FEASIBLE")
        check((barrido["n_satelites"] == k).all(),
              "Todas las soluciones del barrido usan k={} satelites".format(k))
        check(barrido["central_cod"].notna().all(), "Todas las soluciones tienen central")
        for _, fila in barrido.iterrows():
            esperado = fila["lambda"] * fila["A"] + (1 - fila["lambda"]) * fila["B"]
            check(_casi_igual(fila["costo_total"], esperado),
                  "lambda={:.1f}: costo_total = lambda*A + (1-lambda)*B".format(fila["lambda"]))
            check(_casi_igual(fila["costo_total_suma"], fila["A"] + fila["B"]),
                  "lambda={:.1f}: costo_total_suma = A + B".format(fila["lambda"]))

    if not frontera.empty:
        check(frontera["status"].isin(["OPTIMAL", "FEASIBLE"]).all(),
              "La frontera contiene solo soluciones OPTIMAL/FEASIBLE")
        check(frontera["central_cod"].notna().all(), "La frontera tiene central en todas las filas")
        check(frontera["n_satelites"].eq(k).all(),
              "La frontera usa k={} satelites".format(k))
        dominada = False
        for i in range(len(frontera)):
            for j in range(len(frontera)):
                if i != j and _domina(frontera.iloc[i], frontera.iloc[j]):
                    dominada = True
        check(not dominada, "Ningun punto de la frontera esta dominado")
        check(frontera["A"].is_monotonic_increasing or frontera["B"].is_monotonic_increasing,
              "La frontera esta ordenada por al menos un eje de costo")

    # 2. Estabilidad
    print("\n--- 2. Estabilidad en escenarios.csv ---")
    estabilidad = _leer("estabilidad_escenarios.csv",
                        dtype={"central_cod": str, "satelites_cods": str})
    anios = meta.get("parametros", {}).get("anios_estabilidad", [2024, 2028])

    if not estabilidad.empty:
        columnas = {
            "anio", "id_escenario", "oferta", "consumo", "mezcla", "central",
            "central_cod", "satelites", "satelites_cods", "satelites_zonas",
            "costo_recoleccion", "costo_distribucion", "costo_total",
            "costo_total_suma", "status", "cambia_central_vs_base",
        }
        check(columnas.issubset(set(estabilidad.columns)),
              "La tabla de estabilidad tiene las columnas pedidas")
        check(estabilidad["status"].isin(["OPTIMAL", "FEASIBLE"]).all(),
              "Todos los escenarios de estabilidad tienen solucion")
        check(estabilidad["central_cod"].notna().all(),
              "Todos los escenarios de estabilidad tienen central")
        check((estabilidad["n_satelites"] == k).all(),
              "Todos los escenarios de estabilidad usan k={} satelites".format(k))
        zonas_ok = estabilidad["satelites_zonas"].fillna("").map(
            lambda s: len([x for x in str(s).split(";") if x.strip()])).eq(k)
        check(bool(zonas_ok.all()), "Cada escenario reporta la zona de sus k satelites")
        for anio in anios:
            grupo = estabilidad[estabilidad["anio"] == anio]
            check(len(grupo) == 27,
                  "Anio {}: 27 escenarios guardados ({})".format(anio, len(grupo)))
            check(grupo["id_escenario"].is_unique,
                  "Anio {}: escenarios sin duplicados".format(anio))
            check(grupo["es_base"].sum() == 1,
                  "Anio {}: exactamente un escenario base".format(anio))
            base = grupo[grupo["es_base"]]
            if not base.empty:
                b = base.iloc[0]
                check(bool(b["cambia_central_vs_base"]) is False,
                      "Anio {}: el escenario base no cambia de central".format(anio))
                check(bool(b["cambia_satelites_vs_base"]) is False,
                      "Anio {}: el escenario base no cambia de satelites".format(anio))

        for _, fila in estabilidad.iterrows():
            esperado = lam * fila["A"] + (1 - lam) * fila["B"]
            check(_casi_igual(fila["costo_total"], esperado),
                  "{}: costo_total coherente con lambda".format(fila["id_escenario"]))
            check(_casi_igual(fila["costo_total_suma"], fila["A"] + fila["B"]),
                  "{}: costo_total_suma = A + B".format(fila["id_escenario"]))
            check(pd.notna(fila["cambia_central_vs_base"]),
                  "{}: se reporta si cambia la central".format(fila["id_escenario"]))

        cambios = estabilidad[estabilidad["cambia_central_vs_base"] == True]  # noqa: E712
        print("  Info: {} de {} escenarios cambian de central respecto al base de su anio.".format(
            len(cambios), len(estabilidad)))

    # 3. Comparacion libre vs zonas
    print("\n--- 3. Comparacion libre vs zonas ---")
    comparacion = _leer("comparacion_libre_vs_zonas.csv",
                        dtype={"central_cod": str, "satelites_cods": str})
    resumen = _leer("comparacion_libre_vs_zonas_resumen.csv",
                    dtype={"central_libre": str, "central_zonas": str})

    if not comparacion.empty:
        check(set(comparacion["modo"]) == {"libre", "zonas"},
              "La comparacion tiene los modos libre y zonas")
        check(comparacion["id_escenario"].nunique() == 1,
              "Ambos modos usan el mismo escenario")
        check(comparacion["lambda"].nunique() == 1 and comparacion["k"].nunique() == 1,
              "Ambos modos usan el mismo lambda y k")
        check(comparacion["status"].isin(["OPTIMAL", "FEASIBLE"]).all(),
              "Ambos modos tienen solucion")
        check((comparacion["n_satelites"] == k).all(),
              "Ambos modos usan k={} satelites".format(k))
        zonas_ok = comparacion["satelites_zonas"].fillna("").map(
            lambda s: len([x for x in str(s).split(";") if x.strip()])).eq(k)
        check(bool(zonas_ok.all()), "Ambos modos reportan la zona de sus k satelites")

        libre = comparacion[comparacion["modo"] == "libre"].iloc[0]
        zonas = comparacion[comparacion["modo"] == "zonas"].iloc[0]
        check(_casi_igual(libre["delta_objetivo_vs_libre"], 0.0),
              "La fila libre tiene delta de objetivo cero")
        check(bool(libre["misma_central_que_libre"]) is True,
              "La fila libre coincide consigo misma en central")
        check(_casi_igual(
            zonas["delta_objetivo_vs_libre"], zonas["costo_total"] - libre["costo_total"]),
            "El delta de objetivo de zonas es correcto")
        check(_casi_igual(
            zonas["delta_costo_total_suma_vs_libre"],
            zonas["costo_total_suma"] - libre["costo_total_suma"]),
            "El delta de costo total fisico de zonas es correcto")

    if not resumen.empty and not comparacion.empty:
        r = resumen.iloc[0]
        check(r["id_escenario"] == comparacion["id_escenario"].iloc[0],
              "El resumen corresponde al escenario comparado")
        check(_casi_igual(r["delta_objetivo"], zonas["costo_total"] - libre["costo_total"]),
              "El resumen reporta el delta de objetivo")
        check(bool(r["misma_central"]) == bool(
            str(zonas["central_cod"]) == str(libre["central_cod"])),
            "El resumen reporta correctamente si la central cambia")

    # 4. Metadatos y huellas
    print("\n--- 4. Metadatos ---")
    if meta:
        salidas = meta.get("salidas", {})
        for nombre in ("frontera_pareto_base.csv", "estabilidad_escenarios.csv",
                       "comparacion_libre_vs_zonas.csv"):
            check(nombre in salidas, "metadata.json registra {}".format(nombre))
        if "frontera_pareto_base.csv" in salidas:
            ruta = SALIDA / "frontera_pareto_base.csv"
            check(salidas["frontera_pareto_base.csv"]["sha256"] != "",
                  "La frontera tiene huella SHA256")

    print("\n" + "=" * 74)
    print("RESUMEN DE VERIFICACION")
    print("=" * 74)
    print("[OK] Exitos: {}".format(len(EXITOS)))
    print("[FAIL] Errores: {}".format(len(ERRORES)))

    if ERRORES:
        print("\nERRORES ENCONTRADOS:")
        for e in ERRORES:
            print(e)
        return 1

    print("\nTODAS LAS VERIFICACIONES PASARON.")
    print("Los resultados de optimizacion estan listos para el informe final.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
