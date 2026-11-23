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


ESCENARIOS = ("bajo", "base", "alto")

# Rangos y pasos de los controles (coinciden con los widgets de Streamlit y los límites
# históricos del tablero). Se usan para validar la configuración recibida.
RADIO_MIN, RADIO_MAX = 20, 80
CAPTACION_MIN, CAPTACION_MAX = 5, 50
CAPACIDAD_MIN, CAPACIDAD_MAX = 20000, 200000


def construir_config(
    datos_html: dict[str, Any],
    cod_dane: str | None = None,
    radio_km: int = 40,
    captacion_pct: int = 20,
    capacidad_t: int = 100000,
    escenario: str = "base",
) -> dict[str, Any]:
    """Valida y normaliza la configuración de los cinco parámetros de la pantalla 4.

    El código DANE se resuelve contra los municipios del payload (no por posición en un
    selector). Si no se entrega o no existe, no se fija sede y el HTML usa su valor por
    defecto (la mejor sede por área). Lanza ValueError si un valor numérico está fuera de
    rango o el escenario no es válido.
    """
    ids = {m.get("id") for m in datos_html.get("muns", [])}

    cod = None
    if cod_dane is not None:
        cod = str(cod_dane)
        if cod not in ids:
            raise ValueError("cod_dane {!r} no está en los municipios del tablero".format(cod))

    radio = int(radio_km)
    if not (RADIO_MIN <= radio <= RADIO_MAX):
        raise ValueError("radio_km fuera de rango [{}, {}]: {}".format(RADIO_MIN, RADIO_MAX, radio))

    capt = int(captacion_pct)
    if not (CAPTACION_MIN <= capt <= CAPTACION_MAX):
        raise ValueError("captacion_pct fuera de rango [{}, {}]: {}".format(CAPTACION_MIN, CAPTACION_MAX, capt))

    cap = int(capacidad_t)
    if not (CAPACIDAD_MIN <= cap <= CAPACIDAD_MAX):
        raise ValueError("capacidad_t fuera de rango [{}, {}]: {}".format(CAPACIDAD_MIN, CAPACIDAD_MAX, cap))

    esc = str(escenario)
    if esc not in ESCENARIOS:
        raise ValueError("escenario inválido: {!r} (use {})".format(esc, ", ".join(ESCENARIOS)))

    return {
        "cod_dane": cod,            # None o código DANE válido del payload
        "radio_km": radio,          # km
        "captacion_pct": capt,      # porcentaje (0-100), no fracción
        "capacidad_t": cap,         # toneladas por año
        "escenario": esc,           # "bajo" | "base" | "alto"
    }


def _inyectar_config(html: str, config: dict[str, Any] | None) -> str:
    """Inserta window.__CFG__ con la configuración antes del bloque de datos del tablero.

    El JSON se serializa con json.dumps (sin concatenar valores a mano) y se escapa para que
    no pueda romper el contexto <script> ni el HTML. Si config es None, no inyecta nada y el
    HTML conserva sus valores predeterminados.
    """
    if not config:
        return html
    payload = json.dumps(config, ensure_ascii=True)
    # Evita que una secuencia </script> o comentarios HTML cierren el contexto del script.
    payload = (
        payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    )
    bloque = "<script>window.__CFG__ = {};</script>\n".format(payload)
    marcador = "<script>\nconst D = "
    idx = html.find(marcador)
    if idx == -1:
        # Reserva: insertar antes del primer <script> que define D.
        idx = html.find("<script>")
    return html[:idx] + bloque + html[idx:]


def generar_html_tablero(
    ruta_html: Path | str,
    produccion: pd.DataFrame,
    config: dict[str, Any] | None = None,
) -> str:
    """Devuelve el HTML del tablero con las cifras actualizadas desde el CSV.

    Si se entrega `config` (dict de construir_config), se inyecta como window.__CFG__ para
    fijar sede, radio, captación, capacidad y escenario. Sin `config`, el HTML conserva sus
    valores predeterminados (compatibilidad con las llamadas existentes).
    """
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
    html = html[: coincidencia.start(1)] + nuevo_json + html[coincidencia.end(1) :]
    return _inyectar_config(html, config)
