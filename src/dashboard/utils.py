"""
Utilidades para cargar los datos del tablero Streamlit.
Todos los paths son relativos a la raiz del repo.
"""

from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
DATA_CLEAN = ROOT / "data" / "clean"
DATA_RES = ROOT / "data" / "results" / "ML_Ce"


@st.cache_data
def cargar_oferta_escenarios():
    """Carga oferta_escenarios.csv: producto, cod_dane, año, oferta_bajo/base/alto."""
    path = DATA_RES / "oferta_escenarios.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype={"cod_dane": str})


@st.cache_data
def cargar_oferta_departamento():
    """Carga oferta_departamento.csv: producto, año, oferta_bajo/base/alto (suma de municipios)."""
    path = DATA_RES / "oferta_departamento.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data
def cargar_coherencia():
    """Carga coherencia_jerarquica.csv."""
    path = DATA_RES / "coherencia_jerarquica.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data
def cargar_municipios_coordenadas():
    """Carga municipios_coordenadas.csv: cod_dane, municipio, lat, lon."""
    path = DATA_CLEAN / "municipios_coordenadas.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype={"cod_dane": str})


@st.cache_data
def cargar_destinos_coordenadas():
    """Carga destinos_coordenadas.csv: id_destino, nombre, lat, lon."""
    path = DATA_CLEAN / "destinos_coordenadas.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data
def cargar_matriz_tiempos():
    """Carga matriz_tiempos.csv: origen, destino, minutos, distancia_km, metodo."""
    path = DATA_CLEAN / "matriz_tiempos.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype={"origen": str, "destino": str})


@st.cache_data
def cargar_produccion_limpia():
    """Carga produccion_valle_clean.csv para serie histórica."""
    path = DATA_CLEAN / "produccion_valle_clean.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype={"cod_dane": str})


@st.cache_data
def cargar_lista_productos():
    """Carga lista_productos.csv: producto, familia, estado, ranking_toneladas."""
    path = DATA_CLEAN / "lista_productos.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def obtener_productos_disponibles(df_oferta):
    """Devuelve lista ordenada de productos únicos."""
    if df_oferta.empty:
        return []
    return sorted(df_oferta["producto"].unique())


def obtener_municipios_por_producto(df_oferta, producto, ano=2024):
    """Devuelve municipios que tienen oferta para un producto y año dados."""
    if df_oferta.empty:
        return pd.DataFrame()
    sub = df_oferta[(df_oferta["producto"] == producto) & (df_oferta["año"] == ano)]
    return sub


def obtener_serie_historica(df_produccion, producto, cod_dane):
    """Devuelve serie histórica de producción (anio, produccion_t) para un producto-municipio."""
    if df_produccion.empty:
        return pd.DataFrame()
    sub = df_produccion[
        (df_produccion["producto"] == producto) & (df_produccion["cod_dane"] == cod_dane)
    ][["anio", "produccion_t"]].sort_values("anio")
    return sub


def obtener_pronostico_municipio(df_oferta, producto, cod_dane):
    """Devuelve pronóstico 2024-2028 para un producto-municipio."""
    if df_oferta.empty:
        return pd.DataFrame()
    sub = df_oferta[
        (df_oferta["producto"] == producto) & (df_oferta["cod_dane"] == cod_dane)
    ][["año", "oferta_bajo", "oferta_base", "oferta_alto"]].sort_values("año")
    return sub