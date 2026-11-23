"""
Verificacion de la sincronizacion del tablero central (HTML) con el CSV.

Ejecuta: python src/dashboard/test_tablero_central.py
"""

import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "dashboard"))

from tablero_central import (  # noqa: E402
    CATEGORIAS,
    calcular_series_municipios,
    generar_html_tablero,
)

ERRORES = []
EXITOS = []


def check(condicion, mensaje):
    if condicion:
        EXITOS.append("  [OK] {}".format(mensaje))
    else:
        ERRORES.append("  [FAIL] {}".format(mensaje))


def main():
    print("=" * 70)
    print("VERIFICACION DEL TABLERO CENTRAL: datos sincronizados con el CSV")
    print("=" * 70)
    print()

    ruta_produccion = ROOT / "data" / "clean" / "produccion_valle_clean.csv"
    ruta_html = ROOT / "src" / "dashboard" / "assets" / "tablero_central_acopio_valle.html"
    check(ruta_produccion.exists(), "produccion_valle_clean.csv existe")
    check(ruta_html.exists(), "tablero_central_acopio_valle.html existe")
    if not ruta_produccion.exists() or not ruta_html.exists():
        return resumen()

    produccion = pd.read_csv(ruta_produccion, dtype={"cod_dane": str})
    check(len(produccion) > 0, "El CSV de produccion carga correctamente")
    check(
        {"anio", "cod_dane", "producto", "familia", "ha_sembradas", "produccion_t"}.issubset(
            produccion.columns
        ),
        "El CSV tiene las columnas necesarias",
    )

    print("\n--- 1. Calculo por municipio ---")
    series = calcular_series_municipios(produccion)
    check(len(series) == 42, "Se calculan los 42 municipios ({})".format(len(series)))
    check(
        all(len(v["ha"]) == len(CATEGORIAS) for v in series.values()),
        "Cada municipio tiene las 5 categorias",
    )
    check(
        all(all(x >= 0 for x in v["ha"]) for v in series.values()),
        "Las hectareas no son negativas",
    )
    check(
        all(v["t"][0] <= v["t"][1] <= v["t"][2] for v in series.values()),
        "Produccion ordenada: bajo <= base <= alto",
    )

    print("\n--- 2. Contraste independiente contra el CSV ---")
    cali = produccion[produccion["cod_dane"] == "76001"]
    cali_ha = cali[
        (cali["producto"] == "Plátano") & cali["anio"].between(2021, 2023)
    ]["ha_sembradas"].mean()
    cali_anual = (
        cali[(cali["familia"] == "Frutales") & cali["anio"].between(2014, 2023)]
        .groupby("anio")["produccion_t"]
        .sum()
    )
    cali_base = cali_anual.loc[2021:2023].mean()
    esperado = [
        int(round(cali_anual.min())),
        int(round(cali_base)),
        int(round(cali_anual.max())),
    ]
    check(
        abs(series["76001"]["ha"][0] - round(float(cali_ha), 1)) <= 0.05,
        "Cali: hectareas de platano coinciden con el CSV",
    )
    check(series["76001"]["t"] == esperado, "Cali: produccion bajo/base/alto coincide")

    print("\n--- 3. HTML generado ---")
    html = generar_html_tablero(ruta_html, produccion)
    coincidencia = re.search(r"const D = (\{.*?\});\s*\n", html, re.S)
    check(coincidencia is not None, "El HTML mantiene el bloque de datos")
    if not coincidencia:
        return resumen()

    datos = json.loads(coincidencia.group(1))
    check(len(datos["muns"]) == 42, "El HTML generado conserva los 42 municipios")
    check(len(datos["dots"]) == 701, "El mapa conserva los puntos de hectareas")
    check("NaN" not in html, "El HTML no contiene valores NaN")
    check(
        "Vista de cobertura" in html,
        "El pie del tablero explica el alcance de la vista",
    )
    ids_csv = set(series)
    ids_html = {m["id"] for m in datos["muns"]}
    check(ids_csv == ids_html, "Los municipios del HTML tienen datos en el CSV")
    actualizados = all(
        m["id"] in series
        and m["ha"] == series[m["id"]]["ha"]
        and m["t"] == series[m["id"]]["t"]
        for m in datos["muns"]
    )
    check(actualizados, "Las hectareas y la produccion del HTML se actualizan desde el CSV")

    original = json.loads(
        re.search(
            r"const D = (\{.*?\});\s*\n",
            ruta_html.read_text(encoding="utf-8"),
            re.S,
        ).group(1)
    )
    geometria_ok = all(
        a.get("d") == b.get("d") and a.get("x") == b.get("x") and a.get("y") == b.get("y")
        for a, b in zip(original["muns"], datos["muns"])
    )
    check(geometria_ok, "La geometria del mapa no se modifica")
    recuperable_ok = all(
        a.get("g") == b.get("g") for a, b in zip(original["muns"], datos["muns"])
    )
    check(recuperable_ok, "El recuperable se conserva como referencia original")
    check(
        "no se recalcula desde el CSV" in html,
        "El HTML aclara que el recuperable no se recalcula",
    )

    total_t = [sum(m["t"][i] for m in datos["muns"]) for i in range(3)]
    ventana_base = produccion[
        (produccion["familia"] == "Frutales")
        & produccion["anio"].between(2021, 2023)
    ]
    base_por_municipio = (
        ventana_base.groupby(["cod_dane", "anio"])["produccion_t"]
        .sum()
        .groupby("cod_dane")
        .mean()
    )
    check(
        abs(total_t[1] - int(round(base_por_municipio.sum()))) <= len(series),
        "La produccion base total coincide con el CSV (tolerancia de redondeo)",
    )
    check(
        sum(sum(m["ha"]) for m in datos["muns"]) > 0,
        "Las hectareas del HTML son mayores que cero",
    )

    print("\n--- 4. Comparacion territorial centro-norte vs sur (calculo) ---")

    def _hav(a, b):
        radio_tierra = 6371.0
        rad = math.pi / 180.0
        p1 = a["lat"] * rad
        p2 = b["lat"] * rad
        dl = (b["lon"] - a["lon"]) * rad
        h = (
            math.sin((p2 - p1) / 2) ** 2
            + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        )
        return 2 * radio_tierra * math.asin(math.sqrt(h))

    dist = [[_hav(a, b) for b in datos["muns"]] for a in datos["muns"]]
    total_ha = sum(sum(m["ha"]) for m in datos["muns"])

    def _area(i):
        return sum(
            sum(m["ha"])
            for j, m in enumerate(datos["muns"])
            if dist[i][j] <= 40
        )

    def _ton(i):
        return sum(
            m["t"][1]
            for j, m in enumerate(datos["muns"])
            if dist[i][j] <= 40
        )

    centro_norte = [
        i for i, m in enumerate(datos["muns"]) if m["s"] in ("Centro", "Norte")
    ]
    sur = [i for i, m in enumerate(datos["muns"]) if m["s"] == "Sur"]
    mejor_cn = max(centro_norte, key=_area)
    mejor_sur = max(sur, key=_area)
    check(
        _area(mejor_cn) / total_ha > 0.5,
        "A 40 km, el centro-norte cubre mas de la mitad del area",
    )
    razon = _ton(mejor_cn) / _ton(mejor_sur)
    check(
        1.85 <= razon < 2.0,
        "A 40 km, el centro-norte cubre {:.2f} veces el volumen captable del sur "
        "(comparacion descriptiva)".format(razon),
    )
    razon_area = _area(mejor_cn) / _area(mejor_sur)
    check(
        2.9 <= razon_area <= 3.2,
        "A 40 km, el centro-norte cubre {:.2f} veces el area del sur".format(razon_area),
    )

    print("\n--- 5. Exploracion: sin modo de presentacion, controles visibles ---")
    texto = ruta_html.read_text(encoding="utf-8")
    cuerpo = texto.split("const D =")[0]  # excluye el payload de datos
    check("Cobertura y capacidad de una central de acopio" in cuerpo,
          "El encabezado usa el titulo descriptivo nuevo")
    check("enfocar(" not in texto and "classList.toggle(\"f1\"" not in texto,
          "No queda la funcion enfocar() ni el modo de presentacion f1/f2/f3")
    for muerto in ("app.f1", "app.f2", "app.f3", "solo-f1", "#pregunta-1", "#veredicto"):
        check(muerto not in cuerpo, "No queda la regla/elemento de presentacion: {}".format(muerto))
    for pid in ('id="pregunta-1"', 'id="pregunta-2"', 'id="veredicto"'):
        check(pid not in cuerpo, "No queda el bloque de pregunta/veredicto: {}".format(pid))
    check('id="frase"' not in cuerpo and '"frase"' not in texto,
          "pintar() no referencia elementos retirados (frase/q1/q2)")
    check('"q1"' not in texto and '"q2"' not in texto,
          "No quedan referencias DOM a q1/q2")
    # Radio y captacion visibles, fuera de 'Ajustes'
    check('id="c-radio"' in cuerpo and 'id="c-capt"' in cuerpo,
          "Radio y captacion son controles visibles")
    check('id="ajustes"' not in cuerpo and ">Ajustes<" not in cuerpo,
          "El desplegable 'Ajustes' fue retirado")
    # Seccion de comparacion territorial independiente y siempre visible
    check('id="comparacion"' in cuerpo and "Comparación territorial" in cuerpo,
          "La comparacion territorial es una seccion independiente y titulada")
    check("display:none" not in texto.split("#comparacion")[1][:40],
          "La comparacion no esta oculta por CSS")
    # Recuperable en detalle secundario con su aclaracion
    check('id="recuperable"' in cuerpo and "no sincronizada con el CSV" in cuerpo,
          "El recuperable queda en un detalle secundario con la aclaracion visible")
    # Sin veredicto de hipotesis en el texto visible
    for prohibido in ("Hipótesis", "veredicto", "alcanza el doble", "no alcanza el doble"):
        check(prohibido not in cuerpo,
              "No queda lenguaje de hipotesis/veredicto en el cuerpo: '{}'".format(prohibido))

    return resumen()


def resumen():
    print()
    print("=" * 70)
    print("RESUMEN DE VERIFICACION")
    print("=" * 70)
    for linea in EXITOS:
        print(linea)
    for linea in ERRORES:
        print(linea)
    print()
    print("[OK] Exitos: {}".format(len(EXITOS)))
    print("[FAIL] Errores: {}".format(len(ERRORES)))
    if ERRORES:
        print("\nHAY VERIFICACIONES FALLIDAS.")
        return 1
    print("\nTODAS LAS VERIFICACIONES PASARON.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
