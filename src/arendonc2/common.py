"""
Utilidades compartidas por los módulos de arendonc2 (tareas #2, #3, #4).

Centraliza: rutas del repo, carga de configuración, normalización de nombres
de municipio, y lectores de los archivos de datos (siempre con cod_dane como texto).
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA_CLEAN = ROOT / "data" / "clean"
DATA_RAW = ROOT / "data" / "raw"
DATA_RES = ROOT / "data" / "results"
DATA_RES_ML = DATA_RES / "ML_Ce"
DATA_GEO = DATA_RAW / "geo"
CONFIG = ROOT / "config" / "arendonc2" / "parametros.yaml"
DOCS = ROOT / "docs" / "arendonc2"

# Carpeta de salida propia para no pisar resultados de otros autores en revisión.
# Los entregables "oficiales" (zonas.csv, excedentes.csv, escenarios.csv) van a
# data/results/ por contrato; los intermedios/auditoría a data/results/arendonc2/.
DATA_RES_OUT = DATA_RES / "arendonc2"

# Alias de nombres de municipio (nuestros datos -> clave normalizada de GADM).
_ALIAS_GADM = {
    "calimadarien": "calima",
    "buga": "guadalajaradebuga",
    "cali": "santiagodecali",
}


def cargar_config() -> dict:
    """Lee config/arendonc2/parametros.yaml."""
    with open(CONFIG, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def norm_nombre(s: str) -> str:
    """Normaliza un nombre de municipio: minúsculas, sin tildes, solo alfanumérico, sin espacios."""
    s = str(s).lower().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def clave_gadm(nombre_municipio: str) -> str:
    """Clave para emparejar un municipio nuestro con el polígono de GADM."""
    n = norm_nombre(nombre_municipio)
    return _ALIAS_GADM.get(n, n)


# Lectores de datos (cod_dane como texto para no perder ceros iniciales)

def leer_municipios_coordenadas() -> pd.DataFrame:
    return pd.read_csv(DATA_CLEAN / "municipios_coordenadas.csv", dtype={"cod_dane": str})


def leer_oferta_escenarios() -> pd.DataFrame:
    df = pd.read_csv(DATA_RES_ML / "oferta_escenarios.csv", dtype={"cod_dane": str})
    return df.rename(columns={"año": "anio"}) if "año" in df.columns else df


def leer_oferta_valor() -> pd.DataFrame:
    df = pd.read_csv(DATA_RES_ML / "oferta_escenarios_valor.csv", dtype={"cod_dane": str})
    return df.rename(columns={"año": "anio"}) if "año" in df.columns else df


def leer_matriz_tiempos() -> pd.DataFrame:
    return pd.read_csv(
        DATA_CLEAN / "matriz_tiempos.csv", dtype={"origen": str, "destino": str}
    )


def leer_consumo_percapita() -> pd.DataFrame:
    return pd.read_csv(DATA_CLEAN / "consumo_percapita.csv")


def leer_produccion_valle() -> pd.DataFrame:
    return pd.read_csv(DATA_CLEAN / "produccion_valle_clean.csv", dtype={"cod_dane": str})


def leer_lista_productos() -> pd.DataFrame:
    return pd.read_csv(DATA_CLEAN / "lista_productos.csv")


def asegurar_directorios() -> None:
    for d in (DATA_RES_OUT, DATA_RES_ML, DOCS):
        d.mkdir(parents=True, exist_ok=True)
