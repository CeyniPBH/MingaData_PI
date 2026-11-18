"""
Datos vivos para el tablero central de acopio (HTML).

El tablero visual conserva su diseno y su geometria, pero las cifras de
hectareas y produccion se recalculan desde produccion_valle_clean.csv para
que no queden congeladas en el HTML.

Ventanas de datos (iguales a las del tablero original):
- Hectareas: promedio 2021-2023 de ha_sembradas, por categoria.
- Produccion: total anual 2014-2023; base = promedio 2021-2023,
  bajo = peor anio y alto = mejor anio del periodo.
- El indicador "recuperable" (g) se conserva del analisis original; el resto
  de cifras se recalcula desde el CSV.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

CATEGORIAS = ("Plátano", "Aguacate", "Cítricos", "Banano", "Otros frutales")
CATEGORIAS_BASE = ("Plátano", "Aguacate", "Cítricos", "Banano")

ANIO_HA_INICIO = 2021
ANIO_HA_FIN = 2023
ANIO_T_INICIO = 2014
ANIO_T_FIN = 2023

COLUMNAS_REQUERIDAS = {
    "anio",
    "cod_dane",
    "producto",
    "familia",
    "ha_sembradas",
    "produccion_t",
}

PATRON_DATOS = re.compile(r"const D = (\{.*?\});\s*\n", re.DOTALL)


def _categoria(producto: str) -> str:
    """Agrupa cada producto en una de las cinco categorias del tablero."""
    return producto if producto in CATEGORIAS_BASE else "Otros frutales"


def calcular_series_municipios(produccion: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Calcula hectareas y produccion por municipio."""
    faltantes = COLUMNAS_REQUERIDAS - set(produccion.columns)
    if faltantes:
        raise ValueError(
            "Faltan columnas en produccion: {}".format(", ".join(sorted(faltantes)))
        )

    frutales = produccion[produccion["familia"] == "Frutales"].copy()
    if frutales.empty:
        return {}

    frutales["categoria"] = frutales["producto"].map(_categoria)

    # Hectareas promedio por producto en la ventana del tablero.
    ventana = frutales[
        frutales["anio"].between(ANIO_HA_INICIO, ANIO_HA_FIN)
    ].copy()
    por_producto = (
        ventana.groupby(["cod_dane", "categoria", "producto"], as_index=False)
        .agg(ha=("ha_sembradas", "mean"))
    )
    por_categoria = (
        por_producto.groupby(["cod_dane", "categoria"], as_index=False)
        .agg(ha=("ha", "sum"))
    )

    # Serie anual de produccion para los escenarios bajo/base/alto.
    anual = (
        frutales[frutales["anio"].between(ANIO_T_INICIO, ANIO_T_FIN)]
        .groupby(["cod_dane", "anio"])["produccion_t"]
        .sum()
    )

    datos: dict[str, dict[str, Any]] = {}
    for cod in sorted(frutales["cod_dane"].unique()):
        sub = por_categoria[por_categoria["cod_dane"] == cod].set_index("categoria")

        ha = []
        for categoria in CATEGORIAS:
            valor = float(sub.loc[categoria, "ha"]) if categoria in sub.index else 0.0
            if pd.isna(valor):
                valor = 0.0
            ha.append(round(valor, 1))

        if cod in anual.index.get_level_values(0):
            serie = anual.loc[cod].dropna()
        else:
            serie = pd.Series(dtype=float)

        if not serie.empty:
            serie_base = serie[serie.index.isin([2021, 2022, 2023])]
            base = float(serie_base.mean()) if not serie_base.empty else float(serie.mean())
            bajo = float(serie.min())
            alto = float(serie.max())
        else:
            base = bajo = alto = 0.0

        datos[cod] = {
            "ha": ha,
            "t": [int(round(bajo)), int(round(base)), int(round(alto))],
        }

    return datos


def generar_html_tablero(ruta_html: Path | str, produccion: pd.DataFrame) -> str:
    """Devuelve el HTML del tablero con las cifras actualizadas desde el CSV."""
    ruta = Path(ruta_html)
    html = ruta.read_text(encoding="utf-8")

    coincidencia = PATRON_DATOS.search(html)
    if not coincidencia:
        raise ValueError("No se encontro el bloque de datos del tablero en {}".format(ruta))

    datos = calcular_series_municipios(produccion)
    datos_html = json.loads(coincidencia.group(1))

    for municipio in datos_html.get("muns", []):
        valores = datos.get(municipio.get("id"))
        if valores:
            municipio["ha"] = valores["ha"]
            municipio["t"] = valores["t"]

    nuevo_json = json.dumps(datos_html, ensure_ascii=False, separators=(",", ":"))
    return html[: coincidencia.start(1)] + nuevo_json + html[coincidencia.end(1) :]
